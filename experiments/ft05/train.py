"""Opt-in Unsloth training recipe. No GPU run was performed during preparation."""
import argparse
import hashlib
import importlib.metadata
import inspect
import json
import re
from pathlib import Path
from ft05 import load, split, evaluate, compare, load_frozen, strict_json

MODEL = 'Qwen/Qwen2.5-1.5B-Instruct'
PACKAGES = ('unsloth', 'torch', 'transformers', 'trl', 'datasets', 'peft')


def check_config(config):
    if config.get('model') != MODEL or not re.fullmatch(r'[a-f0-9]{40}', config.get('model_revision') or ''):
        raise ValueError('pin_model_revision')
    if config.get('synthetic_only') is not True:
        raise ValueError('synthetic_only')
    if config.get('gpu_budget_approved') is not True or config.get('dependency_reviewed') is not True:
        raise ValueError('gpu_and_dependency_review_required')
    versions = config.get('package_versions', {})
    if set(versions) != set(PACKAGES) or any(not isinstance(v, str) or not v for v in versions.values()):
        raise ValueError('pin_all_package_versions')
    return versions


def infer(model, tokenizer, rows):
    from unsloth import FastLanguageModel
    import torch
    FastLanguageModel.for_inference(model)
    model.eval()
    result = {}
    with torch.inference_mode():
        for row in rows:
            # Only user text is provided to inference; never the expected answer.
            prompt = tokenizer.apply_chat_template(row['messages'][:-1], tokenize=False, add_generation_prompt=True)
            inputs = tokenizer(prompt, return_tensors='pt', add_special_tokens=False).to(model.device)
            output = model.generate(**inputs, max_new_tokens=96, do_sample=False)
            result[row['id']] = tokenizer.decode(output[0][inputs['input_ids'].shape[-1]:], skip_special_tokens=True)
    score = evaluate(rows, result)
    score['model_inference_executed'] = True
    return score, result


def run(dataset, config_path, output, execute=False, frozen_dir=None):
    # Safe default validates preparation only; does not import GPU libraries.
    rows = load(dataset)
    parts = split(rows)
    plan = {'mode': 'plan', 'counts': {k: len(v) for k, v in parts.items()},
            'model': MODEL, 'network_executed': False, 'trained': False}
    if not execute:
        return plan
    if frozen_dir is None:
        raise ValueError('frozen_split_required')
    parts, frozen_sha256 = load_frozen(dataset, frozen_dir)
    config = strict_json(Path(config_path).read_text())
    versions = check_config(config)
    for package, version in versions.items():
        if importlib.metadata.version(package) != version:
            raise ValueError('package_version_mismatch')
    output = Path(output)
    if output.exists():
        raise ValueError('output_already_exists')
    # Import Unsloth before Transformers/Torch as required by its runtime.
    from unsloth import FastLanguageModel
    import torch
    from datasets import Dataset
    from trl import SFTTrainer, SFTConfig
    if not torch.cuda.is_available():
        raise ValueError('cuda_required')
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=MODEL, revision=config['model_revision'], max_seq_length=2048,
        load_in_4bit=True, trust_remote_code=False)
    texts = {k: [tokenizer.apply_chat_template(r['messages'], tokenize=False,
                add_generation_prompt=False) for r in records] for k, records in parts.items()}
    if any(len(tokenizer(t, add_special_tokens=False)['input_ids']) > 2048
           for group in texts.values() for t in group):
        raise ValueError('sequence_would_be_truncated')
    output.mkdir(parents=True)
    baseline, before = infer(model, tokenizer, parts['test'])
    (output / 'model-baseline.json').write_text(json.dumps(baseline, indent=2))
    (output / 'predictions-model-original.json').write_text(json.dumps(before, indent=2))
    model = FastLanguageModel.get_peft_model(model, r=16, lora_alpha=16,
        target_modules=['q_proj', 'k_proj', 'v_proj', 'o_proj', 'gate_proj', 'up_proj', 'down_proj'],
        random_state=3407)
    FastLanguageModel.for_training(model)
    params = inspect.signature(SFTConfig).parameters
    length_key = 'max_length' if 'max_length' in params else 'max_seq_length'
    args = SFTConfig(output_dir=str(output / 'checkpoints'), dataset_text_field='text',
        per_device_train_batch_size=2, gradient_accumulation_steps=4,
        num_train_epochs=3, learning_rate=2e-4, optim='adamw_8bit',
        report_to='none', seed=3407, packing=False,
        save_strategy='epoch', save_total_limit=2, **{length_key: 2048})
    trainer_params = inspect.signature(SFTTrainer).parameters
    token_key = 'processing_class' if 'processing_class' in trainer_params else 'tokenizer'
    trainer = SFTTrainer(model=model, args=args,
        train_dataset=Dataset.from_dict({'text': texts['train']}),
        eval_dataset=Dataset.from_dict({'text': texts['validation']}), **{token_key: tokenizer})
    trainer.train()
    validation = trainer.evaluate()
    (output / 'validation.json').write_text(json.dumps(validation, indent=2))
    finetuned, after = infer(model, tokenizer, parts['test'])
    (output / 'model-finetuned.json').write_text(json.dumps(finetuned, indent=2))
    (output / 'predictions-model-personalized.json').write_text(json.dumps(after, indent=2))
    comparison = compare(parts['test'], before, after)
    comparison.update(original=baseline, personalized=finetuned, model_inference_executed=True)
    (output / 'comparison.json').write_text(json.dumps(comparison, indent=2))
    model.save_pretrained(str(output / 'adapter'))
    tokenizer.save_pretrained(str(output / 'adapter'))
    (output / 'chat-template.txt').write_text(tokenizer.chat_template)
    # GGUF export may build/download llama.cpp: it is a separate opt-in stage.
    if config.get('gguf_export_approved') is True:
        model.save_pretrained_gguf(str(output / 'gguf'), tokenizer, quantization_method='q4_k_m')
    manifest = {'model': MODEL, 'revision': config['model_revision'], 'versions': versions,
        'dataset_sha256': hashlib.sha256(Path(dataset).read_bytes()).hexdigest(),
        'frozen_manifest_sha256': frozen_sha256,
        'config_sha256': hashlib.sha256(Path(config_path).read_bytes()).hexdigest(),
        'test_ids': [r['id'] for r in parts['test']],
        'chat_template_sha256': hashlib.sha256(tokenizer.chat_template.encode()).hexdigest(),
        'trained': True, 'gguf_export_requested': config.get('gguf_export_approved') is True,
        'ollama_tested': False, 'llama_cpp_tested': False}
    (output / 'run.json').write_text(json.dumps(manifest, indent=2))
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('dataset')
    parser.add_argument('--config', default='training-config.json')
    parser.add_argument('--output', default='training-run')
    parser.add_argument('--train', action='store_true')
    parser.add_argument('--frozen', help='Directory created by ft05.py --training-reviewed')
    args = parser.parse_args()
    print(json.dumps(run(args.dataset, args.config, args.output, args.train, args.frozen), indent=2))
