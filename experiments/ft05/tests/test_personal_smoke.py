import ast
import json
import tempfile
import unittest
from pathlib import Path

from auto_pilot import write_auto_dataset
from ft05 import prepare
from personal_smoke import REVISION, preflight, sha256, validate_messages
from train import MODEL


class PersonalSmokeTests(unittest.TestCase):
    def test_colab_starts_with_actions_off_and_no_saved_outputs(self):
        notebook = json.loads(
            (Path(__file__).resolve().parents[1] / 'FT05-PERSONAL-COLAB.ipynb')
            .read_text(encoding='utf-8'))
        config = ''.join(notebook['cells'][1]['source'])
        for flag in ('FETCH_SOURCE', 'MOUNT_DRIVE', 'RUN_PERSONAL_TEST',
                     'FREEZE_REVIEWED', 'INSTALL_DEPS', 'RUN_TRAINING'):
            self.assertIn(flag + ' = False', config)
        for cell in notebook['cells']:
            if cell['cell_type'] == 'code':
                self.assertEqual(cell['outputs'], [])
                self.assertIsNone(cell['execution_count'])
                ast.parse(''.join(cell['source']))

    def test_new_messages_are_unlabelled_unique_and_screened(self):
        rows = [{'id': 'one', 'text': 'Pedido fictício sobre remessa sem data.'},
                {'id': 'two', 'text': 'Quero consultar uma opção de pagamento.'}]
        self.assertEqual(validate_messages(rows), rows)
        with self.assertRaisesRegex(ValueError, 'expected_id_and_text_only'):
            validate_messages([{**rows[0], 'urgencia': 'alta'}])
        with self.assertRaisesRegex(ValueError, 'duplicate_message_text'):
            validate_messages([rows[0], {'id': 'three', 'text': rows[0]['text']}])
        with self.assertRaisesRegex(ValueError, 'possible_sensitive_data'):
            validate_messages([{'id': 'three', 'text': 'Escreva para pessoa@example.com'}])

    def test_preflight_refuses_changed_source_or_incomplete_adapter(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            corpus, frozen, run_dir = root / 'corpus.jsonl', root / 'frozen', root / 'run'
            write_auto_dataset(corpus)
            frozen_meta = prepare(corpus, frozen, automated=True)
            (run_dir / 'adapter').mkdir(parents=True)
            (run_dir / 'adapter' / 'adapter_config.json').write_text('{}')
            weights = run_dir / 'adapter' / 'adapter_model.safetensors'
            weights.write_bytes(b'fixture-only')
            meta = {'model': MODEL, 'loaded_model_name': MODEL,
                    'revision': REVISION, 'exact_model_name_required': True,
                    'review_mode': 'synthetic_machine_checked',
                    'human_reviewed': False, 'trained': True,
                    'dataset_sha256': sha256(corpus),
                    'frozen_manifest_sha256': sha256(frozen / 'manifest.json'),
                    'versions': {name: 'test' for name in
                                 ('unsloth', 'torch', 'transformers', 'trl', 'datasets', 'peft')}}
            # load_frozen returns the hash of the exact frozen manifest bytes.
            self.assertEqual(meta['frozen_manifest_sha256'], sha256(frozen / 'manifest.json'))
            (run_dir / 'run.json').write_text(json.dumps(meta))
            self.assertEqual(preflight(run_dir, corpus, frozen, versions=False)['meta'], meta)
            weights.unlink()
            with self.assertRaisesRegex(ValueError, 'adapter_incomplete'):
                preflight(run_dir, corpus, frozen, versions=False)
            weights.write_bytes(b'fixture-only')
            corpus.write_text(corpus.read_text() + '\n')
            with self.assertRaisesRegex(ValueError, 'training_corpus_changed'):
                preflight(run_dir, corpus, frozen, versions=False)


if __name__ == '__main__':
    unittest.main()
