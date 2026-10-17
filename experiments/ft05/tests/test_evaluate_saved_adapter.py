import unittest

from evaluate_saved_adapter import STRESS, summarize, validate_stress
from ft05 import load


class SavedAdapterStressTests(unittest.TestCase):
    def test_stress_cases_balanced_distinct_and_unreviewed(self):
        rows = load(STRESS)
        original = load(STRESS.with_name('candidates-216.jsonl'))
        self.assertTrue(validate_stress(rows, original))
        self.assertEqual(len(rows), 24)
        self.assertFalse(any(row['reviewed'] for row in rows))

    def test_report_retains_each_error_and_does_not_claim_human_review(self):
        rows = load(STRESS)
        predictions = {row['id']: row['messages'][-1]['content'] for row in rows}
        predictions['s03-entrega-media'] = '{"categoria":"entrega","urgencia":"alta"}'
        report = summarize(rows, predictions)
        self.assertEqual(report['n'], 24)
        self.assertEqual(report['score']['exact_match'], 23 / 24)
        self.assertEqual(report['score']['category_macro_f1_observed'], 1)
        self.assertEqual([case['id'] for case in report['errors']], ['s03-entrega-media'])
        self.assertFalse(report['human_reviewed'])
        self.assertFalse(report['production_ready'])
        self.assertFalse(report['training_performed'])


if __name__ == '__main__':
    unittest.main()
