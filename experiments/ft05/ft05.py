"""Original offline FT05 preparation. No network, model or credential access."""
import argparse
import hashlib
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

CATEGORIES = {'entrega', 'pagamento', 'cancelamento', 'outro'}
URGENCIES = {'alta', 'media', 'baixa'}


def strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate_json_key')
            result[key] = value
        return result
    def invalid(_):
        raise ValueError('nonfinite_json')
    return json.loads(text, object_pairs_hook=pairs, parse_constant=invalid)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':')).encode()).hexdigest()


def normalize(text):
    text = unicodedata.normalize('NFKC', text).casefold()
    return ' '.join(re.findall(r'\w+', text))


def target(text):
    value = strict_json(text)
    if (type(value) is not dict or set(value) != {'categoria', 'urgencia'}
            or type(value['categoria']) is not str or type(value['urgencia']) is not str
            or value['categoria'] not in CATEGORIES or value['urgencia'] not in URGENCIES):
        raise ValueError('invalid_target')
    return value


def validate(rows, training=False):
    if not isinstance(rows, list) or not 1 <= len(rows) <= 500:
        raise ValueError('dataset_size')
    if training and not 200 <= len(rows) <= 500:
        raise ValueError('need_200_to_500_reviewed_examples')
    seen, labels = set(), {}
    for row in rows:
        if type(row) is not dict or set(row) != {'id', 'group_id', 'synthetic', 'reviewed', 'messages'}:
            raise ValueError('invalid_record')
        for key in ('id', 'group_id'):
            if type(row[key]) is not str or not re.fullmatch(r'[a-z0-9_-]{1,64}', row[key]):
                raise ValueError('invalid_identifier')
        if row['id'] in seen:
            raise ValueError('duplicate_id')
        seen.add(row['id'])
        if row['synthetic'] is not True or type(row['reviewed']) is not bool:
            raise ValueError('synthetic_only')
        if training and row['reviewed'] is not True:
            raise ValueError('review_required')
        messages = row['messages']
        if (type(messages) is not list or len(messages) != 2
                or [m.get('role') if type(m) is dict else None for m in messages] != ['user', 'assistant']):
            raise ValueError('expected_user_assistant_pair')
        for message in messages:
            if (set(message) != {'role', 'content'} or type(message['content']) is not str
                    or not message['content'].strip() or len(message['content']) > 6000):
                raise ValueError('invalid_message')
            # Heuristic tripwire, NOT anonymization or a guarantee of absence of PII.
            if re.search(r'\S+@\S+|\b\d[\d .()+-]{8,}\d\b|sk-[A-Za-z0-9]{12,}', message['content']):
                raise ValueError('possible_sensitive_data')
        prompt = normalize(messages[0]['content'])
        if not prompt:
            raise ValueError('empty_normalized_prompt')
        answer = target(messages[1]['content'])
        if prompt in labels and labels[prompt] != answer:
            raise ValueError('conflicting_labels')
        labels[prompt] = answer
    return rows


def load(path, training=False):
    with Path(path).open('rb') as source:
        raw = source.read(4_000_001)
    if len(raw) > 4_000_000:
        raise ValueError('dataset_too_large')
    return validate([strict_json(line) for line in raw.decode('utf-8').splitlines() if line.strip()], training)


def split(rows):
    """Union groups AND normalized prompts; transitive overlap stays in one partition.

    Semantically similar paraphrases must share a curated group_id. No semantic
    deduplication or representativeness guarantee is claimed.
    """
    validate(rows)
    parent = list(range(len(rows)))
    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    seen = {}
    for i, row in enumerate(rows):
        for key in (('group', row['group_id']), ('prompt', normalize(row['messages'][0]['content']))):
            if key in seen:
                parent[root(i)] = root(seen[key])
            else:
                seen[key] = i
    components = {}
    for i, row in enumerate(rows):
        components.setdefault(root(i), []).append(row)
    groups = sorted(components.values(), key=lambda g: digest(sorted(r['id'] for r in g)))
    if len(groups) < 3:
        raise ValueError('need_three_independent_groups')
    ntest, nval = max(1, len(groups) // 5), max(1, len(groups) // 10)
    result = {'test': [], 'validation': [], 'train': []}
    for i, group in enumerate(groups):
        part = 'test' if i < ntest else 'validation' if i < ntest + nval else 'train'
        result[part].extend(sorted(group, key=lambda r: r['id']))
    return result


def baseline(prompt):
    text = normalize(prompt)
    for word, category, urgency in [('cancel', 'cancelamento', 'alta'),
                                     ('entreg', 'entrega', 'alta'), ('cheg', 'entrega', 'alta'),
                                     ('pag', 'pagamento', 'media'), ('parcel', 'pagamento', 'media')]:
        if word in text:
            return {'categoria': category, 'urgencia': urgency}
    return {'categoria': 'outro', 'urgencia': 'baixa'}


def evaluate(rows, predictions):
    validate(rows)
    if type(predictions) is not dict or set(predictions) != {r['id'] for r in rows}:
        raise ValueError('prediction_ids_mismatch')
    valid = exact = 0
    confusion = Counter()
    for row in rows:
        expected = target(row['messages'][-1]['content'])
        try:
            actual = target(predictions[row['id']])
            valid += 1
            exact += actual == expected
            label = actual['categoria']
        except (ValueError, TypeError):
            label = 'INVALID'
        confusion[(expected['categoria'], label)] += 1
    f1 = []
    for label in sorted(CATEGORIES):
        tp = confusion[label, label]
        fp = sum(n for (a, b), n in confusion.items() if b == label and a != label)
        fn = sum(n for (a, b), n in confusion.items() if a == label and b != label)
        if tp + fp + fn:
            f1.append(2 * tp / (2 * tp + fp + fn))
    return {'n': len(rows), 'valid_json_rate': valid / len(rows),
            'exact_match': exact / len(rows), 'category_macro_f1_observed': sum(f1) / len(f1),
            'confusion': [{'expected': a, 'predicted': b, 'n': n} for (a, b), n in sorted(confusion.items())],
            'scope': 'synthetic_only', 'model_inference_executed': False}


def prepare(source, destination):
    rows = load(source)
    parts = split(rows)
    destination = Path(destination)
    # Exclusive directory avoids accidentally replacing an earlier experiment.
    destination.mkdir(parents=True, exist_ok=False)
    manifest = {'source_sha256': hashlib.sha256(Path(source).read_bytes()).hexdigest(),
                'synthetic': True, 'training_ready': False, 'partitions': {}}
    for name, items in parts.items():
        content = ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n' for r in items)
        path = destination / (name + '.jsonl')
        path.write_text(content, encoding='utf-8')
        manifest['partitions'][name] = {'count': len(items), 'sha256': hashlib.sha256(content.encode()).hexdigest()}
    predictions = {r['id']: json.dumps(baseline(r['messages'][0]['content'])) for r in parts['test']}
    (destination / 'baseline.json').write_text(json.dumps(evaluate(parts['test'], predictions), indent=2))
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('dataset')
    parser.add_argument('output')
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args.dataset, args.output), indent=2))
    except (ValueError, OSError, UnicodeError):
        parser.exit(2, 'ft05_input_or_output_rejected\n')
