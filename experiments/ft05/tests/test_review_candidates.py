import csv
import tempfile
import unittest
from pathlib import Path

from ft05 import load, load_frozen, normalize, prepare, split, target
from review_candidates import FIELDS, audit, export_sheet, promote
from scenarios import scenarios


SOURCE = Path(__file__).resolve().parents[1] / 'candidates-216.jsonl'


def filled_sheet(sheet):
    with sheet.open(encoding='utf-8', newline='') as handle:
        decisions = list(csv.DictReader(handle))
    for decision in decisions:
        # TEST FIXTURE ONLY: this must never be published as a real review.
        decision.update(decision='approve', reviewer_id='test_fixture',
                        reason='Simulação automatizada apenas para testar o bloqueio.')
    with sheet.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(decisions)
    return decisions


class CandidateReviewTests(unittest.TestCase):
    def test_candidates_are_distinct_balanced_and_never_training_ready(self):
        rows = load(SOURCE)
        report = audit(SOURCE)
        self.assertEqual((report['candidates'], report['reviewed'], report['groups']), (216, 0, 212))
        self.assertFalse(report['training_ready'])
        self.assertEqual(set(report['labels'].values()), {18})
        self.assertEqual(report['unique_normalized_prompts'], 216)
        for row in rows:
            prompt = normalize(row['messages'][0]['content'])
            self.assertNotIn('fictíci', prompt)
            self.assertNotIn('simulad', prompt)
            self.assertNotIn('de teste', prompt)
        original = load(SOURCE.parent / 'synthetic.jsonl') + scenarios()
        self.assertFalse({normalize(r['messages'][0]['content']) for r in rows}
                         & {normalize(r['messages'][0]['content']) for r in original})
        with self.assertRaises(ValueError):
            load(SOURCE, training=True)

    def test_proposed_groups_stay_together_and_holdout_covers_labels(self):
        rows = load(SOURCE)
        parts = split(rows)
        assigned = {r['id']: name for name, rs in parts.items() for r in rs}
        self.assertEqual(parts, split(list(reversed(rows))))
        self.assertEqual({k: len(v) for k, v in parts.items()},
                         {'train': 153, 'validation': 21, 'test': 42})
        for category in ('entrega', 'pagamento', 'cancelamento', 'outro'):
            self.assertEqual(assigned[f'c26-{category}-alta-01'],
                             assigned[f'c26-{category}-alta-02'])
        pairs = {(label['categoria'], label['urgencia'])
                 for r in parts['test'] for label in (target(r['messages'][-1]['content']),)}
        self.assertEqual(len(pairs), 12)

    def test_unfilled_sheet_cannot_promote_and_tampering_is_detected(self):
        with tempfile.TemporaryDirectory() as temp:
            sheet, output = Path(temp) / 'sheet.csv', Path(temp) / 'reviewed.jsonl'
            export_sheet(SOURCE, sheet)
            with self.assertRaisesRegex(ValueError, 'review_decision_incomplete'):
                promote(SOURCE, sheet, output)
            self.assertFalse(output.exists())
            entries = filled_sheet(sheet)
            entries[0]['prompt'] = 'Outro texto que não foi revisado'
            with sheet.open('w', encoding='utf-8', newline='') as handle:
                writer = csv.DictWriter(handle, fieldnames=FIELDS)
                writer.writeheader(); writer.writerows(entries)
            with self.assertRaisesRegex(ValueError, 'candidate_changed_since_review_sheet'):
                promote(SOURCE, sheet, output)
            self.assertFalse(output.exists())

    def test_simulated_review_can_promote_and_freeze_without_model(self):
        with tempfile.TemporaryDirectory() as temp:
            sheet, output = Path(temp) / 'sheet.csv', Path(temp) / 'reviewed.jsonl'
            export_sheet(SOURCE, sheet)
            filled_sheet(sheet)
            report = promote(SOURCE, sheet, output)
            self.assertEqual(report['approved'], 216)
            self.assertTrue(all(r['reviewed'] for r in load(output, training=True)))
            frozen = Path(temp) / 'frozen'
            prepare(output, frozen, training=True)
            parts, _ = load_frozen(output, frozen)
            self.assertEqual(sum(map(len, parts.values())), 216)
            self.assertEqual(report['partitions']['test'], len(parts['test']))

    def test_reviewed_pair_cannot_be_assigned_conflicting_labels(self):
        with tempfile.TemporaryDirectory() as temp:
            sheet, output = Path(temp) / 'sheet.csv', Path(temp) / 'reviewed.jsonl'
            export_sheet(SOURCE, sheet)
            entries = filled_sheet(sheet)
            pair = next(x for x in entries if x['id'] == 'c26-entrega-alta-02')
            pair['final_urgency'] = 'baixa'
            with sheet.open('w', encoding='utf-8', newline='') as handle:
                writer = csv.DictWriter(handle, fieldnames=FIELDS)
                writer.writeheader(); writer.writerows(entries)
            with self.assertRaisesRegex(ValueError, 'inconsistent_labels_in_reviewed_group'):
                promote(SOURCE, sheet, output)


if __name__ == '__main__':
    unittest.main()
