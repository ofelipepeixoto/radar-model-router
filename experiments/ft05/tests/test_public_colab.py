import json
import unittest
from pathlib import Path

from build_public_notebook import notebook


ROOT = Path(__file__).resolve().parents[1]


class PublicColabTest(unittest.TestCase):
    def test_notebook_is_reproducible_and_code_is_valid(self):
        saved = json.loads((ROOT / 'FT05-PUBLIC-COLAB.ipynb').read_text())
        self.assertEqual(saved, notebook())
        for cell in saved['cells']:
            if cell['cell_type'] == 'code':
                compile(''.join(cell['source']), '<public-colab>', 'exec')

    def test_external_actions_are_opt_in_and_private_adapter_not_referenced(self):
        cells = notebook()['cells']
        setup = ''.join(cells[2]['source'])
        for flag in ('FETCH_SOURCE', 'MOUNT_DRIVE', 'PREPARE_CORPUS',
                     'INSTALL_DEPS', 'RUN_TRAINING', 'RUN_SMOKE',
                     'GPU_BUDGET_CONFIRMED', 'DEPENDENCIES_REVIEWED'):
            self.assertIn(flag + ' = False', setup)
        all_text = ''.join(''.join(c['source']) for c in cells)
        self.assertNotIn('piloto-auto-001', all_text)
        self.assertNotIn('run-002-g4', all_text)
        self.assertIn('if RUN_TRAINING:', all_text)
        self.assertIn('not RUN_DIR.exists()', all_text)
        self.assertIn('automated=True', all_text)


if __name__ == '__main__':
    unittest.main()
