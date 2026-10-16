import json
import tempfile
import unittest
from pathlib import Path

from auto_pilot import EXCLUDED, expected_rows, split_auto, write_auto_dataset
from ft05 import load_frozen, prepare, target
from train import run


class AutomatedPilotTests(unittest.TestCase):
    def test_gated_corpus_and_frozen_holdout(self):
        rows = expected_rows()
        self.assertEqual(len(rows), 208)
        self.assertFalse(any(row['reviewed'] for row in rows))
        self.assertFalse(set(EXCLUDED) & {row['id'] for row in rows})
        parts = split_auto(rows)
        self.assertEqual({key: len(value) for key, value in parts.items()},
                         {'train': 162, 'validation': 12, 'test': 34})
        self.assertEqual(parts, split_auto(list(reversed(rows))))
        membership = {row['id']: name for name, items in parts.items() for row in items}
        self.assertEqual(membership['c26-pagamento-alta-01'],
                         membership['c26-pagamento-alta-13'])
        self.assertEqual(membership['c26-outro-alta-03'],
                         membership['c26-outro-alta-17'])
        self.assertEqual(len({row['group_id'] for row in parts['train']}) +
                         len({row['group_id'] for row in parts['validation']}) +
                         len({row['group_id'] for row in parts['test']}),
                         len({row['group_id'] for row in rows}))
        expected_labels = {(a, b) for a in ('entrega', 'pagamento', 'cancelamento', 'outro')
                           for b in ('alta', 'media', 'baixa')}
        for items in parts.values():
            self.assertEqual({(v['categoria'], v['urgencia']) for row in items
                              for v in [target(row['messages'][-1]['content'])]}, expected_labels)
        with tempfile.TemporaryDirectory() as directory:
            source, frozen = Path(directory) / 'auto.jsonl', Path(directory) / 'frozen'
            report = write_auto_dataset(source)
            self.assertFalse(report['human_reviewed'])
            manifest = prepare(source, frozen, automated=True)
            self.assertTrue(manifest['training_ready'])
            self.assertEqual(manifest['review_mode'], 'synthetic_machine_checked')
            loaded, _ = load_frozen(source, frozen)
            self.assertEqual(loaded, parts)
            self.assertFalse(run(source, 'none', 'none')['trained'])
            changed = source.read_text().replace('O acesso à conta', 'A entrada na conta')
            source.write_text(changed)
            with self.assertRaisesRegex(ValueError, 'source_changed_after_freeze'):
                load_frozen(source, frozen)

    def test_machine_check_cannot_be_claimed_by_arbitrary_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'auto.jsonl'
            write_auto_dataset(source)
            rows = source.read_text().splitlines()
            first = json.loads(rows[0]); first['reviewed'] = True
            rows[0] = json.dumps(first)
            source.write_text('\n'.join(rows) + '\n')
            with self.assertRaisesRegex(ValueError, 'automated_dataset_changed'):
                write_auto_dataset(source)
            with self.assertRaises(ValueError):
                prepare(source, Path(directory) / 'frozen', automated=True)
            with self.assertRaisesRegex(ValueError, 'review_required'):
                prepare(source, Path(directory) / 'human', training=True)


if __name__ == '__main__':
    unittest.main()
