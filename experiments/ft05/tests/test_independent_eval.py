import tempfile
import unittest
from pathlib import Path

from independent_eval import (FIELDS, REVIEW_FIELDS, prepare, read_csv, sha256,
                              score, seal, write_csv, write_json)


class IndependentEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source.csv'
        write_csv(self.source, FIELDS,
                  [{'id': f'msg_{i:03}', 'text': f'Pedido fictício inédito sobre assunto {i}.'}
                   for i in range(40)])
        self.bundle = self.root / 'bundle'
        prepare(self.source, self.bundle, n=30, seed=42, frame='Pedidos fictícios de teste')

    def fill(self, name, reviewer, urgency='media', disagreement=False):
        rows = read_csv(self.bundle / name, REVIEW_FIELDS)
        for i, row in enumerate(rows):
            row.update(categoria='entrega', urgencia='alta' if disagreement and i == 0 else urgency,
                       reason='Análise independente do pedido', reviewer_id=reviewer)
        write_csv(self.bundle / name, REVIEW_FIELDS, rows)

    def test_sampling_is_reproducible_and_blind(self):
        other = self.root / 'other'
        prepare(self.source, other, n=30, seed=42, frame='Pedidos fictícios de teste')
        self.assertEqual((self.bundle / 'sample.csv').read_bytes(), (other / 'sample.csv').read_bytes())
        self.assertEqual(len(read_csv(self.bundle / 'sample.csv', FIELDS)), 30)
        for row in read_csv(self.bundle / 'reviewer-a.csv', REVIEW_FIELDS):
            self.assertEqual([row[k] for k in REVIEW_FIELDS[2:]], ['', '', '', ''])
        self.assertNotIn('predicted', (self.bundle / 'reviewer-a.csv').read_text())

    def test_seal_requires_two_distinct_reviewers_and_third_for_conflict(self):
        self.fill('reviewer-a.csv', 'a')
        with self.assertRaisesRegex(ValueError, 'review_incomplete'):
            seal(self.bundle, self.root / 'sealed')
        self.fill('reviewer-b.csv', 'a')
        with self.assertRaisesRegex(ValueError, 'independent_reviewers_required'):
            seal(self.bundle, self.root / 'sealed')
        self.fill('reviewer-b.csv', 'b', disagreement=True)
        with self.assertRaisesRegex(ValueError, 'adjudicate_exactly_disagreements'):
            seal(self.bundle, self.root / 'sealed')
        rows = read_csv(self.bundle / 'adjudication.csv', REVIEW_FIELDS)
        rows[0].update(categoria='entrega', urgencia='media', reason='Sem prazo iminente', reviewer_id='c')
        write_csv(self.bundle / 'adjudication.csv', REVIEW_FIELDS, rows)
        manifest = seal(self.bundle, self.root / 'sealed')
        self.assertEqual(manifest['disagreements'], 1)
        self.assertNotEqual(manifest['human_reviewed'], True)

    def test_scoring_requires_sealed_gold_and_matching_prediction_provenance(self):
        self.fill('reviewer-a.csv', 'a')
        self.fill('reviewer-b.csv', 'b')
        sealed = self.root / 'sealed'
        manifest = seal(self.bundle, sealed)
        prediction_dir = self.root / 'prediction'
        prediction_dir.mkdir()
        sample = read_csv(self.bundle / 'sample.csv', FIELDS)
        predictions = {row['id']: '{"categoria":"entrega","urgencia":"media"}' for row in sample}
        predictions[sample[0]['id']] = '{"categoria":"entrega","urgencia":"alta"}'
        write_json(prediction_dir / 'predictions.json', predictions)
        wrong = {'scope': 'independent_private_evaluation', 'sample_sha256': 'bad',
                 'gold_sha256': manifest['gold_sha256'], 'model_inference_executed': True,
                 'training_performed': False, 'predictions_sha256': sha256(prediction_dir / 'predictions.json')}
        write_json(prediction_dir / 'manifest.json', wrong)
        with self.assertRaisesRegex(ValueError, 'incompatible_prediction_manifest'):
            score(self.bundle, sealed, prediction_dir / 'predictions.json', self.root / 'report')
        wrong['sample_sha256'] = manifest['sample_sha256']
        write_json(prediction_dir / 'manifest.json', wrong)
        report = score(self.bundle, sealed, prediction_dir / 'predictions.json', self.root / 'report')
        self.assertEqual((report['sampled'], report['adjudicable'], report['false_high']), (30, 30, 1))
        self.assertEqual(report['missed_high'], 0)
        self.assertFalse(report['production_ready'])
        self.assertEqual(report['exact_match'], 29 / 30)

    def test_modified_sample_rejected(self):
        with (self.bundle / 'sample.csv').open('a', encoding='utf-8') as stream:
            stream.write('extra,alterado\n')
        self.fill('reviewer-a.csv', 'a')
        self.fill('reviewer-b.csv', 'b')
        with self.assertRaisesRegex(ValueError, 'sample_changed'):
            seal(self.bundle, self.root / 'sealed')

    def test_synthetic_overlap_and_csv_formula_rejected(self):
        from ft05 import strict_json
        candidate = strict_json((Path(__file__).resolve().parents[1] / 'candidates-216.jsonl')
                                .read_text(encoding='utf-8').splitlines()[0])
        rows = read_csv(self.source, FIELDS)
        rows[0]['text'] = candidate['messages'][0]['content']
        write_csv(self.source, FIELDS, rows)
        with self.assertRaisesRegex(ValueError, 'exact_synthetic_text_overlap'):
            prepare(self.source, self.root / 'other', n=30, frame='Pedidos fictícios de teste')
        rows[0]['text'] = '=HYPERLINK("https://example.com")'
        write_csv(self.source, FIELDS, rows)
        with self.assertRaisesRegex(ValueError, 'spreadsheet_formula_risk'):
            prepare(self.source, self.root / 'other', n=30, frame='Pedidos fictícios de teste')


if __name__ == '__main__':
    unittest.main()
