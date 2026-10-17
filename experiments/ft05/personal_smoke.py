"""Private, inference-only test of a saved FT05 adapter on new messages."""
import hashlib
import importlib.metadata
import json
import re
import subprocess
import time
from pathlib import Path

from ft05 import load_frozen, normalize, strict_json, target
from train import MODEL, load_pinned_model

REVISION = '5fee7c4ed634dc66c6e318c8ac2897b8b9154536'


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_messages(messages):
    if type(messages) is not list or not 1 <= len(messages) <= 50:
        raise ValueError('messages_must_be_1_to_50')
    ids, texts = set(), set()
    for row in messages:
        if type(row) is not dict or set(row) != {'id', 'text'}:
            raise ValueError('expected_id_and_text_only')
        ident, text = row['id'], row['text']
        if type(ident) is not str or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', ident) or ident in ids:
            raise ValueError('invalid_or_duplicate_id')
        if type(text) is not str or not text.strip() or len(text) > 6000:
            raise ValueError('invalid_message_text')
        normalized = normalize(text)
        if not normalized or normalized in texts:
            raise ValueError('duplicate_message_text')
        # Tripwire, not anonymization. Only fictitious text belongs in this demo.
        if re.search(r'\S+@\S+|\b\d[\d .()+-]{8,}\d\b|sk-[A-Za-z0-9]{12,}', text):
            raise ValueError('possible_sensitive_data')
        ids.add(ident)
        texts.add(normalized)
    return messages


def preflight(run_dir, corpus, frozen, *, versions=True):
    run_dir, corpus, frozen = Path(run_dir), Path(corpus), Path(frozen)
    run_file = run_dir / 'run.json'
    meta = strict_json(run_file.read_text(encoding='utf-8'))
    if (type(meta) is not dict or meta.get('model') != MODEL
            or meta.get('loaded_model_name') != MODEL
            or meta.get('revision') != REVISION
            or meta.get('exact_model_name_required') is not True
            or meta.get('review_mode') != 'synthetic_machine_checked'
            or meta.get('human_reviewed') is not False
            or meta.get('trained') is not True):
        raise ValueError('incompatible_training_run')
    if sha256(corpus) != meta.get('dataset_sha256'):
        raise ValueError('training_corpus_changed')
    _, frozen_hash = load_frozen(corpus, frozen)
    if frozen_hash != meta.get('frozen_manifest_sha256'):
        raise ValueError('training_split_changed')
    adapter = run_dir / 'adapter'
    config, weights = adapter / 'adapter_config.json', adapter / 'adapter_model.safetensors'
    if not config.is_file() or not weights.is_file() or not weights.stat().st_size:
        raise ValueError('adapter_incomplete')
    expected_versions = meta.get('versions')
    if type(expected_versions) is not dict or set(expected_versions) != {
            'unsloth', 'torch', 'transformers', 'trl', 'datasets', 'peft'}:
        raise ValueError('package_versions_missing')
    if versions:
        for package, expected in expected_versions.items():
            if importlib.metadata.version(package) != expected:
                raise ValueError('package_version_mismatch_' + package)
    return {'run_file': run_file, 'meta': meta, 'adapter': adapter,
            'config': config, 'weights': weights, 'corpus_sha256': sha256(corpus),
            'frozen_manifest_sha256': frozen_hash, 'versions_checked': versions}


def run(messages, run_dir, output_dir, *, corpus, frozen):
    validate_messages(messages)
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise ValueError('output_already_exists')
    checked = preflight(run_dir, corpus, frozen)
    # Unsloth must precede Torch/Transformers in this Colab runtime.
    from unsloth import FastLanguageModel
    import torch
    from peft import PeftModel
    if not torch.cuda.is_available():
        raise ValueError('cuda_required')
    meta = checked['meta']
    base, tokenizer, loaded_name = load_pinned_model(FastLanguageModel, REVISION)
    if hashlib.sha256(tokenizer.chat_template.encode()).hexdigest() != meta['chat_template_sha256']:
        raise ValueError('chat_template_changed')
    model = PeftModel.from_pretrained(base, str(checked['adapter']), is_trainable=False)
    FastLanguageModel.for_inference(model)
    model.eval()
    rows = []
    with torch.inference_mode():
        for row in messages:
            prompt = tokenizer.apply_chat_template(
                [{'role': 'user', 'content': row['text']}], tokenize=False,
                add_generation_prompt=True)
            inputs = tokenizer(prompt, return_tensors='pt', add_special_tokens=False).to(model.device)
            started = time.perf_counter()
            generated = model.generate(**inputs, max_new_tokens=96, do_sample=False)
            torch.cuda.synchronize()
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            output_text = tokenizer.decode(
                generated[0][inputs['input_ids'].shape[-1]:], skip_special_tokens=True)
            try:
                parsed, error = target(output_text), None
            except (ValueError, TypeError) as exc:
                parsed, error = None, str(exc)
            rows.append({'id': row['id'], 'text': row['text'],
                         'predicted_text': output_text, 'parsed': parsed,
                         'error': error, 'latency_ms': elapsed_ms})
    try:
        revision = subprocess.check_output(
            ['git', '-C', str(Path(__file__).resolve().parents[2]), 'rev-parse', 'HEAD'],
            text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        revision = None
    manifest = {'scope': 'personal_synthetic_smoke_no_gold_labels',
                'model': loaded_name, 'model_revision': REVISION,
                'code_revision': revision,
                'run_manifest_sha256': sha256(checked['run_file']),
                'adapter_config_sha256': sha256(checked['config']),
                'adapter_weights_sha256': sha256(checked['weights']),
                'corpus_sha256': checked['corpus_sha256'],
                'frozen_manifest_sha256': checked['frozen_manifest_sha256'],
                'versions': meta['versions'], 'training_performed': False,
                'human_reviewed': False, 'model_inference_executed': True}
    report = {'scope': manifest['scope'], 'n': len(rows),
              'valid_json': sum(row['parsed'] is not None for row in rows),
              'all_ids_predicted': True, 'training_performed': False,
              'production_ready': False, 'results': rows}
    output_dir.mkdir(parents=True, exist_ok=False)
    for name, value in (('manifest.json', manifest), ('report.json', report)):
        (output_dir / name).write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return report
