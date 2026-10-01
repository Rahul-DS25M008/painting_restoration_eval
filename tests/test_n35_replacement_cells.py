"""Check replacement generation only; never execute notebook cells or AppTest."""
import ast
import importlib.util
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('n35_builder', ROOT / 'tools/prepare_n35_batch2_cells.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class ReplacementCellTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = builder.NOTEBOOK.read_bytes()
        cls.cells = builder.build_cells(json.loads(cls.before))

    def test_exact_cell_types_and_syntax(self):
        self.assertEqual(len(self.cells), 12)
        self.assertEqual([i for i, c in enumerate(self.cells) if c['cell_type'] == 'markdown'], [0, 1, 7])
        for i, cell in enumerate(self.cells):
            if cell['cell_type'] == 'code':
                ast.parse(cell['source'], filename=f'cell-{i}')
        self.assertEqual(builder.NOTEBOOK.read_bytes(), self.before)

    def test_no_obsolete_tour_or_breakpoint_assertion(self):
        self.assertNotIn('@media (max-width: 1050px)', self.cells[8]['source'])
        self.assertNotIn('Guided tour · 1 / 8', self.cells[10]['source'])
        self.assertIn('app.get("iframe")', self.cells[10]['source'])
        self.assertIn('MuseumVisit.install(window,', self.cells[10]['source'])

    def test_reflow_parser_accepts_current_rules_but_not_missing_reflow(self):
        # Isolated pure parser test: no cell execution and no app import.
        tree = ast.parse(builder.RESPONSIVE)
        parser = next(n for n in tree.body if isinstance(n, ast.FunctionDef))
        namespace = {'re': re}
        exec(compile(ast.Module(body=[parser], type_ignores=[]), '<css-parser-test>', 'exec'), namespace)
        parse = namespace['css_media_blocks']
        blocks = parse((ROOT / 'streamlit_app.py').read_text(encoding='utf-8'))
        self.assertTrue(any(w == 780 and '.foyer-actions' in b and 'position: relative' in b for w, b in blocks))
        self.assertTrue(any(w == 640 and '.museum-nav' in b for w, b in blocks))
        self.assertEqual(parse('body { color: red; }'), [])
        with self.assertRaises(ValueError):
            parse('@media(max-width:640px){ .museum-nav {')

    def test_completion_requires_all_prior_stages_and_keeps_pending_gates(self):
        self.assertIn('REQUIRED_BATCH_1_STAGES', self.cells[6]['source'])
        self.assertIn('OBSERVED_BATCH_2_STAGES != EXPECTED_BATCH_2_STAGES', self.cells[11]['source'])
        self.assertIn('pending_current_release_validation', self.cells[11]['source'])
        self.assertIn('N35 completion: NO', self.cells[11]['source'])

    def test_inventory_and_version_failures_are_not_waived(self):
        cell = self.cells[5]['source']
        self.assertIn('"inventory_freshness"', cell)
        self.assertIn('severity="blocking"', cell)
        self.assertIn('INVENTORY_IS_FRESH', cell)
        self.assertIn('severity="warning"', cell)
        self.assertIn('passed=False', cell)
        self.assertIn('"requirements_pins"', cell)

    def test_render_has_one_copy_control_per_complete_cell(self):
        page = builder.render(self.cells)
        self.assertEqual(page.count('Copy complete cell'), 12)
        self.assertIn('<article>', page)
        self.assertIn('navigator.clipboard.writeText(text)', page)
        self.assertEqual(builder.NOTEBOOK.read_bytes(), self.before)


if __name__ == '__main__':
    unittest.main()
