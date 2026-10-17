import json
import unittest
from pathlib import Path


class PersonalUiNotebookTest(unittest.TestCase):
    def test_ui_requires_opt_in_and_keeps_model_in_session(self):
        notebook = json.loads((Path(__file__).resolve().parents[1] /
                               'FT05-PERSONAL-COLAB.ipynb').read_text())
        cells = [''.join(cell['source']) for cell in notebook['cells']
                 if cell['cell_type'] == 'code']
        for source in cells:
            compile(source, '<personal-colab>', 'exec')
        ui, = [source for source in cells if 'LAUNCH_INTERFACE = False' in source]
        self.assertIn('if LAUNCH_INTERFACE:', ui)
        self.assertIn('preflight(RUN_DIR, CORPUS, FROZEN, versions=True)', ui)
        self.assertIn('botao.on_click(classificar)', ui)
        self.assertIn('torch.inference_mode()', ui)
        self.assertNotIn('share=True', ui)
        self.assertNotIn('save_pretrained', ui)


if __name__ == '__main__':
    unittest.main()
