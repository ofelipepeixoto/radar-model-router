"""Post-hoc synthetic stress check of an existing FT05 adapter; never trains."""
import argparse
import hashlib
import importlib.metadata
import json
import subprocess
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

from ft05 import CATEGORIES, URGENCIES, evaluate, load, load_frozen, normalize, strict_json, target
from train import MODEL, infer, load_pinned_model

STRESS = Path(__file__).with_name('posthoc-stress-v1.jsonl')


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def validate_stress(stress, original):
    if len(stress) != 24 or any(row['reviewed'] for row in stress):
        raise ValueError('posthoc_stress_not_24_unreviewed')
    labels = Counter((label['categoria'], label['urgencia']) for row in stress
                     for label in [target(row['messages'][-1]['content'])])
    if labels != Counter({(category, urgency): 2 for category in CATEGORIES for urgency in URGENCIES}):
        raise ValueError('posthoc_stress_not_balanced')
    if {r['id'] for r in stress} & {r['id'] for r in original}:
        raise ValueError('posthoc_id_overlap')
    old_prompts = [normalize(r['messages'][0]['content']) for r in original]
    for row in stress:
        prompt = normalize(row['messages'][0]['content'])
        if any((match := SequenceMatcher(None, prompt, old)).real_quick_ratio() >= 0.77
               and match.quick_ratio() >= 0.77 and match.ratio() >= 0.77
               for old in old_prompts):
            raise ValueError('posthoc_prompt_too_similar')
    return True


def summarize(rows, predictions):
    score = evaluate(rows, predictions)
    by_label = Counter()
    errors = []
    for row in rows:
        expected = target(row['messages'][-1]['content'])
        key = (expected['categoria'], expected['urgencia'])
        by_label[key, 'total'] += 1
        try:
            correct = target(predictions[row['id']]) == expected
        except (ValueError, TypeError):
            correct = False
        if correct:
            by_label[key, 'correct'] += 1
        else:
            errors.append({'id': row['id'], 'prompt': row['messages'][0]['content'],
                           'expected': expected, 'predicted_text': predictions[row['id']]})
    return {'scope': 'posthoc_synthetic_stress_diagnostic',
            'created_after_frozen_test_review': True, 'human_reviewed': False,
            'training_performed': False, 'production_ready': False,
            'n': len(rows), 'score': score,
            'by_label': [{'category': c, 'urgency': u,
                          'correct': by_label[c, u, 'correct'],
                          'total': by_label[c, u, 'total']}
                         for c in sorted(CATEGORIES) for u in sorted(URGENCIES)],
            'errors': errors}


def run(run_dir, output_dir, corpus, frozen):
    run_dir, output_dir, corpus, frozen = map(Path, (run_dir, output_dir, corpus, frozen))
    if output_dir.exists():
        raise ValueError('output_already_exists')
    source_manifest = run_dir / 'run.json'
    metadata = strict_json(source_manifest.read_text(encoding='utf-8'))
    if (metadata.get('model') != MODEL or metadata.get('loaded_model_name') != MODEL
            or metadata.get('revision') != '5fee7c4ed634dc66c6e318c8ac2897b8b9154536'
            or metadata.get('exact_model_name_required') is not True
            or metadata.get('review_mode') != 'synthetic_machine_checked'
            or metadata.get('human_reviewed') is not False or metadata.get('trained') is not True):
        raise ValueError('incompatible_training_run')
    if sha256(corpus) != metadata.get('dataset_sha256'):
        raise ValueError('training_corpus_changed')
    original, frozen_hash = load_frozen(corpus, frozen)
    if frozen_hash != metadata.get('frozen_manifest_sha256'):
        raise ValueError('training_split_changed')
    original = sum((original[k] for k in ('train', 'validation', 'test')), [])
    stress = load(STRESS)
    validate_stress(stress, original)
    for package, expected in metadata['versions'].items():
        if importlib.metadata.version(package) != expected:
            raise ValueError('package_version_mismatch')
    adapter = run_dir / 'adapter'
    config_file, weights_file = adapter / 'adapter_config.json', adapter / 'adapter_model.safetensors'
    if not config_file.is_file() or not weights_file.is_file():
        raise ValueError('adapter_incomplete')
    # Unsloth must be imported before Torch/Transformers in this runtime.
    from unsloth import FastLanguageModel
    import torch
    from peft import PeftModel
    if not torch.cuda.is_available():
        raise ValueError('cuda_required')
    base, tokenizer, loaded_name = load_pinned_model(FastLanguageModel, metadata['revision'])
    if hashlib.sha256(tokenizer.chat_template.encode()).hexdigest() != metadata['chat_template_sha256']:
        raise ValueError('chat_template_changed')
    model = PeftModel.from_pretrained(base, str(adapter), is_trainable=False)
    _, predictions = infer(model, tokenizer, stress)
    report = summarize(stress, predictions)
    try:
        code_revision = subprocess.check_output(
            ['git', '-C', str(Path(__file__).resolve().parents[2]), 'rev-parse', 'HEAD'],
            text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        code_revision = None
    provenance = {'source_run_manifest_sha256': sha256(source_manifest),
                  'source_run_name': run_dir.name, 'model': MODEL,
                  'revision_requested': metadata['revision'], 'loaded_model_name': loaded_name,
                  'adapter_config_sha256': sha256(config_file),
                  'adapter_weights_sha256': sha256(weights_file),
                  'corpus_sha256': sha256(corpus), 'frozen_manifest_sha256': frozen_hash,
                  'stress_sha256': sha256(STRESS), 'code_revision': code_revision,
                  'human_reviewed': False, 'training_performed': False,
                  'scope': 'posthoc_synthetic_stress_diagnostic'}
    output_dir.mkdir(parents=True, exist_ok=False)
    for name, value in [('predictions.json', predictions), ('report.json', report),
                        ('manifest.json', provenance)]:
        (output_dir / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n',
                                       encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_dir')
    parser.add_argument('output_dir')
    parser.add_argument('--corpus', required=True)
    parser.add_argument('--frozen', required=True)
    args = parser.parse_args()
    result = run(args.run_dir, args.output_dir, args.corpus, args.frozen)
    print(json.dumps({'n': result['n'], 'exact_match': result['score']['exact_match'],
                      'valid_json_rate': result['score']['valid_json_rate'],
                      'errors': result['errors']}, ensure_ascii=False, indent=2))
