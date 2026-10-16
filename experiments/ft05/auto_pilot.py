"""Reproducible machine checks for one synthetic FT05 experiment.

This is not human review or evidence of deployment quality. The exact source
bytes, exclusions and grouping policy are fixed in code. No model/API calls.
"""
import hashlib
import json
from collections import Counter
from pathlib import Path

from ft05 import CATEGORIES, URGENCIES, load, normalize, target, validate

SOURCE = Path(__file__).with_name('candidates-216.jsonl')
SOURCE_SHA256 = '60165fc420553057a0b9e188951753003500bc61631759c3820a6e473f3efbed'
POLICY = 'ft05-synthetic-auto-v1'

# Requests with a plausible competing primary intent are omitted, without
# silently relabelling them to achieve an attractive metric.
EXCLUDED = {
    'c26-pagamento-alta-09': 'Canceled order versus pending debit',
    'c26-pagamento-alta-17': 'Payment block versus delivery deadline',
    'c26-cancelamento-media-08': 'Removing one item versus whole-order cancellation',
    'c26-cancelamento-baixa-08': 'Refund policy versus cancellation policy',
    'c26-cancelamento-baixa-15': 'Right of withdrawal versus general policy',
    'c26-cancelamento-baixa-16': 'Account closure versus subscription cancellation',
    'c26-outro-alta-04': 'Suspicious link versus confirmed account incident',
    'c26-outro-alta-10': 'Brand impersonation versus account access',
}

# Known semantic families share a group even when wording differs. This is a
# narrow, explicit leakage control; unidentified paraphrases may still exist.
FAMILIES = {
    'duplicate-charge': ('c26-pagamento-alta-01', 'c26-pagamento-alta-02',
                         'c26-pagamento-alta-05', 'c26-pagamento-alta-13'),
    'renewal-today': ('c26-cancelamento-alta-01', 'c26-cancelamento-alta-02',
                      'c26-cancelamento-alta-06', 'c26-cancelamento-alta-11',
                      'c26-cancelamento-alta-14', 'c26-cancelamento-alta-17'),
    'unknown-session': ('c26-outro-alta-01', 'c26-outro-alta-02',
                        'c26-outro-alta-05', 'c26-outro-alta-12',
                        'c26-outro-alta-14'),
    'cross-profile': ('c26-outro-alta-03', 'c26-outro-alta-11',
                      'c26-outro-alta-17'),
}


def expected_rows():
    if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError('candidate_source_changed')
    original = load(SOURCE)
    if len(original) != 216 or any(row['reviewed'] for row in original):
        raise ValueError('candidate_source_not_216_unreviewed')
    ids = {row['id'] for row in original}
    members = [ident for group in FAMILIES.values() for ident in group]
    if len(members) != len(set(members)) or not set(members) <= ids or not set(EXCLUDED) <= ids:
        raise ValueError('invalid_group_or_exclusion_ids')
    group_by_id = {ident: 'auto-' + family for family, group in FAMILIES.items()
                   for ident in group}
    result = [{**row, 'group_id': group_by_id.get(row['id'], row['group_id'])}
              for row in original if row['id'] not in EXCLUDED]
    validate(result)
    if not 200 <= len(result) <= 500 or any(row['reviewed'] for row in result):
        raise ValueError('invalid_automated_corpus')
    labels = Counter((target(row['messages'][-1]['content'])['categoria'],
                      target(row['messages'][-1]['content'])['urgencia']) for row in result)
    expected = {(category, urgency) for category in CATEGORIES for urgency in URGENCIES}
    if set(labels) != expected or min(labels.values()) < 15:
        raise ValueError('insufficient_label_coverage')
    prompts = [normalize(row['messages'][0]['content']) for row in result]
    if len(set(prompts)) != len(prompts):
        raise ValueError('duplicate_normalized_prompt')
    groups = {}
    for row in result:
        label = target(row['messages'][-1]['content'])
        key = (label['categoria'], label['urgencia'])
        if groups.setdefault(row['group_id'], key) != key:
            raise ValueError('mixed_label_group')
    parts = split_auto(result)
    for name in ('train', 'validation', 'test'):
        observed = {(label['categoria'], label['urgencia']) for row in parts[name]
                    for label in [target(row['messages'][-1]['content'])]}
        if observed != expected:
            raise ValueError('partition_missing_label_' + name)
    return result


def verify_auto(rows):
    if rows != expected_rows():
        raise ValueError('automated_dataset_changed')
    return True


def split_auto(rows):
    """Stratify by label at group level, without seeing model predictions."""
    validate(rows)
    buckets = {}
    for row in rows:
        label = target(row['messages'][-1]['content'])
        key = (label['categoria'], label['urgencia'])
        buckets.setdefault(key, {}).setdefault(row['group_id'], []).append(row)
    parts = {'train': [], 'validation': [], 'test': []}
    for bucket in buckets.values():
        groups = sorted(bucket.values(), key=lambda items: hashlib.sha256(
            json.dumps(sorted(r['id'] for r in items)).encode()).hexdigest())
        if len(groups) < 10:
            raise ValueError('insufficient_independent_groups')
        ntest, nvalidation = max(1, len(groups) // 5), max(1, len(groups) // 10)
        for i, group in enumerate(groups):
            name = 'test' if i < ntest else 'validation' if i < ntest + nvalidation else 'train'
            parts[name].extend(sorted(group, key=lambda row: row['id']))
    return {name: sorted(items, key=lambda row: row['id']) for name, items in parts.items()}


def write_auto_dataset(destination):
    rows = expected_rows()
    payload = ''.join(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n' for row in rows)
    destination = Path(destination)
    if destination.exists():
        if destination.read_text(encoding='utf-8') != payload:
            raise ValueError('automated_dataset_changed')
    else:
        destination.write_text(payload, encoding='utf-8', errors='strict')
    parts = split_auto(rows)
    return {'review_mode': 'synthetic_machine_checked', 'human_reviewed': False,
            'policy': POLICY, 'candidate_source_sha256': SOURCE_SHA256,
            'dataset_sha256': hashlib.sha256(payload.encode()).hexdigest(),
            'excluded_ids': EXCLUDED, 'included': len(rows),
            'partitions': {name: len(items) for name, items in parts.items()}}
