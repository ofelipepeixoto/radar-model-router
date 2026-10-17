"""Private, blinded evaluation workflow for previously unseen service messages.

Standard library for prepare/seal/score. Only predict imports GPU packages.
This workflow never trains and never changes FT05's 216-candidate review gate.
"""
import argparse
import csv
import hashlib
import importlib.metadata
import json
import random
import re
from collections import Counter
from pathlib import Path

from ft05 import CATEGORIES, URGENCIES, normalize, strict_json, target

POLICY = 'ft05-support-v1 (experiments/ft05/CANDIDATE-REVIEW.md)'
FIELDS = ('id', 'text')
REVIEW_FIELDS = ('id', 'text', 'categoria', 'urgencia', 'reason', 'reviewer_id')
GOLD_FIELDS = ('id', 'categoria', 'urgencia')


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_csv(path, fields):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != list(fields):
            raise ValueError('csv_columns_mismatch')
        rows = list(reader)
    if not rows or any(None in r or any(v is None for v in r.values()) for r in rows):
        raise ValueError('empty_or_malformed_csv')
    return rows


def write_csv(path, fields, rows):
    with Path(path).open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n',
                          encoding='utf-8')


def known_synthetic_prompts():
    root = Path(__file__).parent
    return {normalize(row['messages'][0]['content'])
            for name in ('candidates-216.jsonl', 'synthetic.jsonl', 'posthoc-stress-v1.jsonl')
            for line in (root / name).read_text(encoding='utf-8').splitlines()
            if line.strip() for row in [strict_json(line)]}


def prepare(source, directory, n=60, seed=3407, frame=''):
    source, directory = Path(source), Path(directory)
    if len(frame.strip()) < 10:
        raise ValueError('sampling_frame_description_required')
    rows = read_csv(source, FIELDS)
    if type(n) is not int or not 30 <= n <= 200 or len(rows) < n:
        raise ValueError('sample_size_30_to_200_with_sufficient_source')
    ids, prompts = set(), set()
    synthetic = known_synthetic_prompts()
    for row in rows:
        ident, prompt = row['id'], normalize(row['text'])
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', ident) or ident in ids:
            raise ValueError('invalid_or_duplicate_id')
        if not row['text'].strip() or len(row['text']) > 6000 or not prompt or prompt in prompts:
            raise ValueError('invalid_or_duplicate_text')
        if row['text'].lstrip().startswith(('=', '+', '-', '@')):
            raise ValueError('spreadsheet_formula_risk')
        # Tripwire only. The source must already be de-identified by its owner.
        if re.search(r'\S+@\S+|\b\d[\d .()+-]{8,}\d\b|sk-[A-Za-z0-9]{12,}', row['text']):
            raise ValueError('possible_sensitive_data')
        if prompt in synthetic:
            raise ValueError('exact_synthetic_text_overlap')
        ids.add(ident)
        prompts.add(prompt)
    if directory.exists():
        raise ValueError('output_already_exists')
    sample = random.Random(seed).sample(sorted(rows, key=lambda r: r['id']), n)
    directory.mkdir(parents=True)
    write_csv(directory / 'sample.csv', FIELDS, sample)
    blank = [{**row, 'categoria': '', 'urgencia': '', 'reason': '', 'reviewer_id': ''}
             for row in sample]
    for name in ('reviewer-a.csv', 'reviewer-b.csv', 'adjudication.csv'):
        write_csv(directory / name, REVIEW_FIELDS, blank)
    manifest = {'scope': 'independent_private_evaluation', 'policy': POLICY,
                'source_sha256': sha256(source), 'source_count': len(rows),
                'sample_sha256': sha256(directory / 'sample.csv'), 'sample_count': n,
                'seed': seed, 'sampling': 'uniform_without_replacement_over_all_source_rows',
                'frame_description': frame.strip(),
                'labels_blinded': True, 'review_completed': False,
                'human_reviewed': False, 'training_performed': False,
                'model_inference_executed': False}
    write_json(directory / 'manifest.json', manifest)
    return manifest


def bundle(directory):
    directory = Path(directory)
    manifest = strict_json((directory / 'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('scope') != 'independent_private_evaluation' or manifest.get('policy') != POLICY:
        raise ValueError('invalid_eval_manifest')
    if sha256(directory / 'sample.csv') != manifest['sample_sha256']:
        raise ValueError('sample_changed')
    sample = read_csv(directory / 'sample.csv', FIELDS)
    if len(sample) != manifest['sample_count'] or len({r['id'] for r in sample}) != len(sample):
        raise ValueError('sample_ids_changed')
    return manifest, sample


def labels(directory, filename, sample, *, complete):
    rows = read_csv(Path(directory) / filename, REVIEW_FIELDS)
    if [(r['id'], r['text']) for r in rows] != [(r['id'], r['text']) for r in sample]:
        raise ValueError('review_text_or_order_changed')
    result = {}
    for row in rows:
        filled = any(row[k].strip() for k in REVIEW_FIELDS[2:])
        if complete and not filled:
            raise ValueError('review_incomplete')
        if not filled:
            continue
        if not all(row[k].strip() for k in REVIEW_FIELDS[2:]):
            raise ValueError('partial_review_row')
        if ((row['categoria'], row['urgencia']) != ('indefinida', 'indefinida')
                and (row['categoria'] not in CATEGORIES or row['urgencia'] not in URGENCIES)):
            raise ValueError('invalid_review_label')
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', row['reviewer_id']):
            raise ValueError('invalid_reviewer_id')
        result[row['id']] = row
    reviewers = {r['reviewer_id'] for r in result.values()}
    if len(reviewers) > 1:
        raise ValueError('one_reviewer_per_sheet')
    return result, next(iter(reviewers), None)


def seal(directory, output):
    directory, output = Path(directory), Path(output)
    manifest, sample = bundle(directory)
    if output.exists():
        raise ValueError('output_already_exists')
    a, reviewer_a = labels(directory, 'reviewer-a.csv', sample, complete=True)
    b, reviewer_b = labels(directory, 'reviewer-b.csv', sample, complete=True)
    if reviewer_a == reviewer_b:
        raise ValueError('independent_reviewers_required')
    adjudications, reviewer_c = labels(directory, 'adjudication.csv', sample, complete=False)
    conflicts = {ident for ident in a if (a[ident]['categoria'], a[ident]['urgencia'])
                 != (b[ident]['categoria'], b[ident]['urgencia'])}
    if set(adjudications) != conflicts:
        raise ValueError('adjudicate_exactly_disagreements')
    if conflicts and reviewer_c in {reviewer_a, reviewer_b}:
        raise ValueError('third_reviewer_required')
    gold = []
    for row in sample:
        ident = row['id']
        chosen = adjudications[ident] if ident in conflicts else a[ident]
        gold.append({k: chosen[k] if k != 'id' else ident for k in GOLD_FIELDS})
    output.mkdir(parents=True)
    write_csv(output / 'gold.csv', GOLD_FIELDS, gold)
    review_manifest = {**manifest, 'review_completed': True,
                       'human_reviewed': 'declared_by_identified_reviewers_not_technically_verified',
                       'sample_sha256': sha256(directory / 'sample.csv'),
                       'gold_sha256': sha256(output / 'gold.csv'),
                       'reviewer_sheet_sha256': {name: sha256(directory / name)
                          for name in ('reviewer-a.csv', 'reviewer-b.csv', 'adjudication.csv')},
                       'reviewer_ids': [reviewer_a, reviewer_b] + ([reviewer_c] if conflicts else []),
                       'disagreements': len(conflicts),
                       'indeterminate': sum(r['categoria'] == 'indefinida' for r in gold)}
    write_json(output / 'manifest.json', review_manifest)
    return review_manifest


def sealed(directory, output):
    manifest, sample = bundle(directory)
    review = strict_json((Path(output) / 'manifest.json').read_text(encoding='utf-8'))
    gold_path = Path(output) / 'gold.csv'
    if (review.get('sample_sha256') != manifest['sample_sha256']
            or review.get('gold_sha256') != sha256(gold_path)
            or review.get('review_completed') is not True):
        raise ValueError('gold_or_sample_changed')
    if any(sha256(Path(directory) / name) != expected
           for name, expected in review['reviewer_sheet_sha256'].items()):
        raise ValueError('review_sheet_changed_after_seal')
    gold = read_csv(gold_path, GOLD_FIELDS)
    if [r['id'] for r in gold] != [r['id'] for r in sample]:
        raise ValueError('gold_ids_changed')
    return review, sample, gold


def score(directory, sealed_dir, predictions_path, output):
    review, sample, gold = sealed(directory, sealed_dir)
    predictions_path, output = Path(predictions_path), Path(output)
    if output.exists():
        raise ValueError('output_already_exists')
    prediction_manifest = strict_json((predictions_path.parent / 'manifest.json').read_text(encoding='utf-8'))
    if (prediction_manifest.get('scope') != 'independent_private_evaluation'
            or prediction_manifest.get('sample_sha256') != review['sample_sha256']
            or prediction_manifest.get('gold_sha256') != review['gold_sha256']
            or prediction_manifest.get('predictions_sha256') != sha256(predictions_path)
            or prediction_manifest.get('model_inference_executed') is not True
            or prediction_manifest.get('training_performed') is not False):
        raise ValueError('incompatible_prediction_manifest')
    predictions = strict_json(predictions_path.read_text(encoding='utf-8'))
    if type(predictions) is not dict or set(predictions) != {r['id'] for r in sample}:
        raise ValueError('prediction_ids_mismatch')
    selected = [r for r in gold if r['categoria'] != 'indefinida']
    if not selected:
        raise ValueError('no_adjudicable_cases')
    confusion, by_category = Counter(), Counter()
    valid = exact = false_high = missed_high = 0
    errors = []
    for row in selected:
        try:
            predicted = target(predictions[row['id']])
            valid += 1
            category, urgency = predicted['categoria'], predicted['urgencia']
        except (ValueError, TypeError):
            category = urgency = 'INVALID'
        expected = (row['categoria'], row['urgencia'])
        actual = (category, urgency)
        exact += actual == expected
        confusion[row['urgencia'], urgency] += 1
        by_category[row['categoria'], category] += 1
        false_high += row['urgencia'] != 'alta' and urgency == 'alta'
        missed_high += row['urgencia'] == 'alta' and urgency != 'alta'
        if actual != expected:
            errors.append({'id': row['id'], 'expected': dict(zip(GOLD_FIELDS[1:], expected)),
                           'predicted': dict(zip(GOLD_FIELDS[1:], actual))})
    report = {'scope': 'independent_private_evaluation', 'sampled': len(sample),
              'adjudicable': len(selected), 'indeterminate': len(sample) - len(selected),
              'exact_match': exact / len(selected), 'valid_json_rate': valid / len(selected),
              'false_high': false_high, 'missed_high': missed_high,
              'urgency_confusion': [{'expected': a, 'predicted': b, 'n': count}
                                    for (a, b), count in sorted(confusion.items())],
              'category_confusion': [{'expected': a, 'predicted': b, 'n': count}
                                     for (a, b), count in sorted(by_category.items())],
              'errors': errors, 'training_performed': False, 'production_ready': False,
              'human_reviewed': review['human_reviewed']}
    output.mkdir(parents=True)
    write_json(output / 'report.json', report)
    write_json(output / 'manifest.json', {'sample_sha256': review['sample_sha256'],
               'gold_sha256': review['gold_sha256'], 'review_manifest_sha256': sha256(Path(sealed_dir) / 'manifest.json'),
               'predictions_sha256': sha256(predictions_path),
               'prediction_manifest_sha256': sha256(predictions_path.parent / 'manifest.json'),
               'scope': report['scope'], 'model_inference_executed': True,
               'training_performed': False})
    return report


def predict(directory, sealed_dir, run_dir, output, corpus, frozen):
    """Infer only after labels are sealed; never present predictions in reviewer sheets."""
    review, sample, _ = sealed(directory, sealed_dir)
    run_dir, output = Path(run_dir), Path(output)
    if output.exists():
        raise ValueError('output_already_exists')
    from ft05 import load_frozen
    from train import MODEL, load_pinned_model
    run_manifest = run_dir / 'run.json'
    meta = strict_json(run_manifest.read_text(encoding='utf-8'))
    if (meta.get('model') != MODEL or meta.get('loaded_model_name') != MODEL
            or meta.get('revision') != '5fee7c4ed634dc66c6e318c8ac2897b8b9154536'
            or meta.get('exact_model_name_required') is not True
            or meta.get('review_mode') != 'synthetic_machine_checked'
            or meta.get('human_reviewed') is not False or meta.get('trained') is not True):
        raise ValueError('incompatible_training_run')
    if sha256(corpus) != meta.get('dataset_sha256'):
        raise ValueError('training_corpus_changed')
    _, frozen_hash = load_frozen(corpus, frozen)
    if frozen_hash != meta.get('frozen_manifest_sha256'):
        raise ValueError('training_split_changed')
    for package, version in meta['versions'].items():
        if importlib.metadata.version(package) != version:
            raise ValueError('package_version_mismatch')
    adapter = run_dir / 'adapter'
    config, weights = adapter / 'adapter_config.json', adapter / 'adapter_model.safetensors'
    if not config.is_file() or not weights.is_file():
        raise ValueError('adapter_incomplete')
    from unsloth import FastLanguageModel
    import torch
    from peft import PeftModel
    if not torch.cuda.is_available():
        raise ValueError('cuda_required')
    base, tokenizer, loaded_name = load_pinned_model(FastLanguageModel, meta['revision'])
    if hashlib.sha256(tokenizer.chat_template.encode()).hexdigest() != meta['chat_template_sha256']:
        raise ValueError('chat_template_changed')
    model = PeftModel.from_pretrained(base, str(adapter), is_trainable=False)
    FastLanguageModel.for_inference(model)
    model.eval()
    predictions = {}
    with torch.inference_mode():
        for row in sample:
            prompt = tokenizer.apply_chat_template([{'role': 'user', 'content': row['text']}],
                                                    tokenize=False, add_generation_prompt=True)
            inputs = tokenizer(prompt, return_tensors='pt', add_special_tokens=False).to(model.device)
            generated = model.generate(**inputs, max_new_tokens=96, do_sample=False)
            predictions[row['id']] = tokenizer.decode(
                generated[0][inputs['input_ids'].shape[-1]:], skip_special_tokens=True)
    output.mkdir(parents=True)
    write_json(output / 'predictions.json', predictions)
    write_json(output / 'manifest.json', {'scope': 'independent_private_evaluation',
               'sample_sha256': review['sample_sha256'], 'gold_sha256': review['gold_sha256'],
               'predictions_sha256': sha256(output / 'predictions.json'),
               'run_sha256': sha256(run_manifest), 'adapter_config_sha256': sha256(config),
               'adapter_weights_sha256': sha256(weights), 'corpus_sha256': sha256(corpus),
               'frozen_manifest_sha256': frozen_hash, 'model': loaded_name,
               'model_inference_executed': True, 'training_performed': False})
    return {'predictions': len(predictions), 'model_inference_executed': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    p = commands.add_parser('prepare')
    p.add_argument('source'); p.add_argument('bundle'); p.add_argument('--n', type=int, default=60)
    p.add_argument('--seed', type=int, default=3407)
    p.add_argument('--frame', required=True, help='Collection period, channel and inclusion criteria')
    p = commands.add_parser('seal'); p.add_argument('bundle'); p.add_argument('sealed')
    p = commands.add_parser('predict'); p.add_argument('bundle'); p.add_argument('sealed')
    p.add_argument('run_dir'); p.add_argument('output')
    p.add_argument('--corpus', required=True); p.add_argument('--frozen', required=True)
    p = commands.add_parser('score'); p.add_argument('bundle'); p.add_argument('sealed')
    p.add_argument('predictions'); p.add_argument('output')
    args = parser.parse_args()
    if args.command == 'prepare':
        result = prepare(args.source, args.bundle, args.n, args.seed, args.frame)
    elif args.command == 'seal':
        result = seal(args.bundle, args.sealed)
    elif args.command == 'predict':
        result = predict(args.bundle, args.sealed, args.run_dir, args.output,
                         args.corpus, args.frozen)
    else:
        result = score(args.bundle, args.sealed, args.predictions, args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
