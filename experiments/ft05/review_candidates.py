"""Offline review workflow for FT05 candidate data; no model or network calls."""
import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from ft05 import CATEGORIES, URGENCIES, load, normalize, split, target, validate

POLICY = 'ft05-support-v1'
FIELDS = ('source_sha256', 'id', 'prompt_sha256', 'prompt', 'proposed_category',
          'proposed_urgency', 'proposed_group_id', 'decision', 'final_category',
          'final_urgency', 'final_group_id', 'reason', 'reviewer_id', 'policy_version')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def fingerprint(path):
    return sha(Path(path).read_bytes())


def export_sheet(source, output):
    rows = load(source)
    if not 200 <= len(rows) <= 500 or any(r['reviewed'] for r in rows):
        raise ValueError('need_200_to_500_unreviewed_candidates')
    if Path(output).exists():
        raise ValueError('output_already_exists')
    if any(r['messages'][0]['content'].lstrip().startswith(('=', '+', '-', '@')) for r in rows):
        raise ValueError('unsafe_spreadsheet_value')
    source_hash = fingerprint(source)
    with Path(output).open('x', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            prompt = row['messages'][0]['content']
            label = target(row['messages'][-1]['content'])
            writer.writerow({'source_sha256': source_hash, 'id': row['id'],
                             'prompt_sha256': sha(prompt.encode('utf-8')), 'prompt': prompt,
                             'proposed_category': label['categoria'],
                             'proposed_urgency': label['urgencia'],
                             'proposed_group_id': row['group_id'],
                             'decision': '', 'final_category': label['categoria'],
                             'final_urgency': label['urgencia'],
                             'final_group_id': row['group_id'], 'reason': '',
                             'reviewer_id': '', 'policy_version': POLICY})
    return {'candidates': len(rows), 'source_sha256': source_hash, 'sheet': str(output)}


def promote(source, sheet, output):
    """Apply explicit review decisions. Fields do not prove human identity."""
    candidates = load(source)
    if not 200 <= len(candidates) <= 500 or any(r['reviewed'] for r in candidates):
        raise ValueError('need_200_to_500_unreviewed_candidates')
    if Path(output).exists():
        raise ValueError('output_already_exists')
    by_id = {r['id']: r for r in candidates}
    selected, seen = [], set()
    source_hash = fingerprint(source)
    with Path(sheet).open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != list(FIELDS):
            raise ValueError('review_columns_changed')
        for decision in reader:
            ident = decision['id']
            if ident not in by_id or ident in seen:
                raise ValueError('review_id_mismatch')
            seen.add(ident)
            row = by_id[ident]
            prompt = row['messages'][0]['content']
            label = target(row['messages'][-1]['content'])
            if (decision['source_sha256'] != source_hash
                    or decision['prompt_sha256'] != sha(prompt.encode('utf-8'))
                    or decision['prompt'] != prompt
                    or decision['proposed_category'] != label['categoria']
                    or decision['proposed_urgency'] != label['urgencia']
                    or decision['proposed_group_id'] != row['group_id']):
                raise ValueError('candidate_changed_since_review_sheet')
            if (decision['policy_version'] != POLICY
                    or not re.fullmatch(r'[a-z0-9_-]{2,64}', decision['reviewer_id'] or '')
                    or len((decision['reason'] or '').strip()) < 12):
                raise ValueError('review_decision_incomplete')
            if decision['decision'] not in {'approve', 'exclude'}:
                raise ValueError('decision_must_be_approve_or_exclude')
            if decision['decision'] == 'exclude':
                continue
            category, urgency, group = (decision['final_category'],
                                        decision['final_urgency'], decision['final_group_id'])
            if (category not in CATEGORIES or urgency not in URGENCIES
                    or not re.fullmatch(r'[a-z0-9_-]{1,64}', group or '')):
                raise ValueError('invalid_final_label_or_group')
            selected.append({**row, 'reviewed': True, 'group_id': group,
                             'messages': [row['messages'][0], {'role': 'assistant',
                             'content': json.dumps({'categoria': category, 'urgencia': urgency},
                                                   ensure_ascii=False, separators=(',', ':'))}]})
    if seen != set(by_id):
        raise ValueError('unreviewed_candidates_remaining')
    validate(selected, training=True)
    group_labels = {}
    for row in selected:
        label = target(row['messages'][-1]['content'])
        key = (label['categoria'], label['urgencia'])
        group = row['group_id']
        if group in group_labels and group_labels[group] != key:
            raise ValueError('inconsistent_labels_in_reviewed_group')
        group_labels[group] = key
    partitions = split(selected)
    # A diagnostic gate: each label must be present in train and test, otherwise
    # the comparison would be unable to assess that label on the frozen holdout.
    expected_pairs = {(a, b) for a in CATEGORIES for b in URGENCIES}
    for name in ('train', 'test'):
        labels = [target(row['messages'][-1]['content']) for row in partitions[name]]
        if {(x['categoria'], x['urgencia']) for x in labels} != expected_pairs:
            raise ValueError('partition_missing_label_review_groups_and_exclusions')
    content = ''.join(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n'
                      for row in selected)
    with Path(output).open('x', encoding='utf-8') as handle:
        handle.write(content)
    return {'approved': len(selected), 'excluded': len(candidates) - len(selected),
            'output_sha256': sha(content.encode()),
            'partitions': {name: len(part) for name, part in partitions.items()}}


def audit(source):
    rows = load(source)
    labels = Counter((target(r['messages'][-1]['content'])['categoria'],
                      target(r['messages'][-1]['content'])['urgencia']) for r in rows)
    parts = split(rows)
    return {'candidates': len(rows), 'reviewed': sum(r['reviewed'] for r in rows),
            'groups': len({r['group_id'] for r in rows}),
            'unique_normalized_prompts': len({normalize(r['messages'][0]['content']) for r in rows}),
            'labels': {f'{a}/{b}': labels[a, b] for a, b in sorted(labels)},
            'preview_split_counts': {name: len(part) for name, part in parts.items()},
            'training_ready': all(r['reviewed'] for r in rows)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('audit', 'export', 'promote'))
    parser.add_argument('source')
    parser.add_argument('destination', nargs='?')
    parser.add_argument('review_sheet', nargs='?')
    args = parser.parse_args()
    if args.action == 'audit':
        result = audit(args.source)
    elif args.action == 'export':
        if not args.destination:
            parser.error('export requires a destination CSV')
        result = export_sheet(args.source, args.destination)
    else:
        if not args.destination or not args.review_sheet:
            parser.error('promote requires destination JSONL and review sheet CSV')
        result = promote(args.source, args.review_sheet, args.destination)
    print(json.dumps(result, ensure_ascii=False, indent=2))
