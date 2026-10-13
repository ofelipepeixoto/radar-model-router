import copy
import json
import unittest
from ft05 import split, validate, normalize, baseline, evaluate
from scenarios import scenarios


class ScenarioTests(unittest.TestCase):
    def test_ambiguous_labels_are_unreviewed_proposals_and_expose_baseline_limits(self):
        rows = scenarios()
        validate(rows)
        self.assertTrue(all(r['synthetic'] and r['reviewed'] is False for r in rows))
        predictions = {r['id']: json.dumps(baseline(r['messages'][0]['content'])) for r in rows}
        self.assertLess(evaluate(rows, predictions)['exact_match'], 1)
        # This small corpus cannot be promoted to training merely by toggling flags.
        with self.assertRaisesRegex(ValueError, '200_to_500'): validate(rows, training=True)

    def test_paraphrases_unicode_and_transitive_bridge_never_cross_partitions(self):
        rows = scenarios(); parts = split(rows)
        assigned = {r['id']: name for name, group in parts.items() for r in group}
        self.assertEqual(assigned['indirect'], assigned['paraphrase'])
        self.assertEqual(assigned['unicode'], assigned['normalized'])
        self.assertEqual(assigned['unicode'], assigned['bridge'])
        self.assertEqual(parts, split(list(reversed(rows))))
        self.assertEqual(set(assigned), {r['id'] for r in rows})
        for name, group in parts.items():
            others = [r for key, items in parts.items() if key != name for r in items]
            for key in (lambda r: r['group_id'], lambda r: normalize(r['messages'][0]['content'])):
                self.assertFalse({key(r) for r in group} & {key(r) for r in others})

    def test_conflicting_unicode_duplicate_is_rejected(self):
        rows = copy.deepcopy(scenarios())
        rows[5]['messages'][1]['content'] = '{"categoria":"outro","urgencia":"baixa"}'
        with self.assertRaisesRegex(ValueError, 'conflicting_labels'): validate(rows)

    def test_semantic_group_assignment_is_a_review_responsibility(self):
        rows = scenarios()
        self.assertNotEqual(normalize(rows[2]['messages'][0]['content']),
                            normalize(rows[3]['messages'][0]['content']))
        self.assertEqual(rows[2]['group_id'], rows[3]['group_id'])
