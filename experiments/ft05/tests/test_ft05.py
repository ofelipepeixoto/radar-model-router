import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from ft05 import validate, split, evaluate, strict_json, prepare, normalize, load_frozen, compare
from train import MODEL, run, check_config, load_pinned_model


def rows():
    return [{'id': f'x{i}', 'group_id': f'g{i}', 'synthetic': True, 'reviewed': False,
             'messages': [{'role': 'user', 'content': f'Pedido ficticio variante {i}'},
                          {'role': 'assistant', 'content': '{"categoria":"entrega","urgencia":"alta"}'}]}
            for i in range(12)]


class Tests(unittest.TestCase):
    def test_schema_rejects_bad_records(self):
        for edit in [lambda r: r.update(synthetic=False), lambda r: r.update(reviewed='true'),
                     lambda r: r.update(extra=1), lambda r: r['messages'].reverse(),
                     lambda r: r['messages'][0].update(content='test@example.com'),
                     lambda r: r['messages'][1].update(content='{"categoria":"???","urgencia":"alta"}')]:
            data = rows(); edit(data[0])
            with self.subTest(edit=edit), self.assertRaises(ValueError): validate(data)

    def test_duplicate_keys_and_nonfinite_rejected(self):
        for text in ['{"x":1,"x":2}', '{"x":NaN}']:
            with self.assertRaises(ValueError): strict_json(text)

    def test_conflicting_label(self):
        data = rows(); data[1]['messages'][0]['content'] = data[0]['messages'][0]['content']
        data[1]['messages'][1]['content'] = '{"categoria":"outro","urgencia":"baixa"}'
        with self.assertRaisesRegex(ValueError, 'conflicting'): validate(data)

    def test_transitive_overlap_and_order_invariance(self):
        data = rows(); data[1]['group_id'] = data[0]['group_id']
        data[2]['messages'][0]['content'] = data[1]['messages'][0]['content'].upper() + '!!!'
        parts = split(data)
        assigned = {r['id']: name for name, group in parts.items() for r in group}
        self.assertEqual(assigned['x0'], assigned['x2'])
        self.assertEqual(parts, split(list(reversed(data))))
        self.assertEqual(sum(map(len, parts.values())), len(data))
        for left in parts:
            for right in parts:
                if left == right: continue
                for key in (lambda r: r['group_id'], lambda r: normalize(r['messages'][0]['content'])):
                    self.assertFalse(set(map(key, parts[left])) & set(map(key, parts[right])))

    def test_insufficient_groups(self):
        data = rows()
        for r in data: r['group_id'] = 'same'
        with self.assertRaises(ValueError): split(data)

    def test_evaluation_counts_invalid_and_wrong(self):
        data = rows()[:3]
        predictions = {r['id']: r['messages'][1]['content'] for r in data}
        predictions['x0'] = 'not json'
        predictions['x1'] = '{"categoria":"outro","urgencia":"baixa"}'
        score = evaluate(data, predictions)
        self.assertEqual(score['exact_match'], 1 / 3)
        self.assertEqual(score['valid_json_rate'], 2 / 3)
        self.assertEqual(score['urgency_macro_f1_observed'], 0.25)
        self.assertEqual(sum(c['n'] for c in score['urgency_confusion']), 3)
        self.assertFalse(score['model_inference_executed'])
        predictions['unexpected'] = '{}'
        with self.assertRaises(ValueError): evaluate(data, predictions)

    def test_training_gates(self):
        with self.assertRaises(ValueError): validate(rows(), training=True)
        with self.assertRaises(ValueError): check_config({})

    def test_model_loader_keeps_requested_repo_and_revision(self):
        revision = 'a' * 40
        class Loader:
            @staticmethod
            def from_pretrained(**kwargs):
                self.assertEqual(kwargs['model_name'], MODEL)
                self.assertEqual(kwargs['revision'], revision)
                self.assertIs(kwargs['use_exact_model_name'], True)
                return SimpleNamespace(config=SimpleNamespace(_name_or_path=MODEL)), object()
        _, _, loaded_name = load_pinned_model(Loader, revision)
        self.assertEqual(loaded_name, MODEL)

        class SubstitutingLoader:
            @staticmethod
            def from_pretrained(**kwargs):
                return SimpleNamespace(config=SimpleNamespace(
                    _name_or_path='unsloth/Qwen2.5-1.5B-Instruct-unsloth-bnb-4bit')), object()
        with self.assertRaisesRegex(ValueError, 'model_source_changed'):
            load_pinned_model(SubstitutingLoader, revision)

    def test_same_holdout_comparison_counts_improvements_and_regressions(self):
        data = rows()[:3]
        right = {r['id']: r['messages'][1]['content'] for r in data}
        original, personalized = right.copy(), right.copy()
        original['x0'] = 'invalid'
        personalized['x1'] = 'invalid'
        report = compare(data, original, personalized)
        self.assertEqual(report['improved_ids'], ['x0'])
        self.assertEqual(report['regressed_ids'], ['x1'])
        self.assertEqual(report['delta_exact_match'], 0)
        self.assertEqual(report['delta_urgency_macro_f1'], 0)
        with self.assertRaises(ValueError): compare(data, original, {'x0': '{}'})

    def test_reviewed_freeze_refuses_changed_source_or_partitions(self):
        data = [{'id': f'x{i}', 'group_id': f'g{i}', 'synthetic': True, 'reviewed': True,
                 'messages': [{'role': 'user', 'content': f'Pedido ficticio variante {i}'},
                              {'role': 'assistant', 'content': '{"categoria":"entrega","urgencia":"alta"}'}]}
                for i in range(200)]
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'reviewed.jsonl'
            source.write_text(''.join(json.dumps(r) + '\n' for r in data))
            frozen = Path(directory) / 'frozen'
            self.assertTrue(prepare(source, frozen, training=True)['training_ready'])
            parts, digest = load_frozen(source, frozen)
            self.assertEqual(sum(map(len, parts.values())), 200)
            self.assertEqual(len(digest), 64)
            test = frozen / 'test.jsonl'
            original = test.read_bytes()
            test.write_bytes(original + b'\n')
            with self.assertRaisesRegex(ValueError, 'frozen_partition_changed'):
                load_frozen(source, frozen)
            test.write_bytes(original)
            source.write_text(source.read_text().replace('variante 0', 'variante zero'))
            with self.assertRaisesRegex(ValueError, 'source_changed_after_freeze'):
                load_frozen(source, frozen)

    def test_training_requires_explicit_frozen_split(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'input.jsonl'
            source.write_text(''.join(json.dumps(r) + '\n' for r in rows()))
            with self.assertRaisesRegex(ValueError, 'frozen_split_required'):
                run(source, 'nonexistent', Path(directory) / 'output', execute=True)

    def test_prepare_and_plan_no_dependencies(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'input.jsonl'
            source.write_text(''.join(json.dumps(r) + '\n' for r in rows()))
            destination = Path(directory) / 'prepared'
            manifest = prepare(source, destination)
            self.assertFalse(manifest['training_ready'])
            self.assertFalse(run(source, 'nonexistent', 'unused')['trained'])
            with self.assertRaises(FileExistsError): prepare(source, destination)


if __name__ == '__main__': unittest.main()
