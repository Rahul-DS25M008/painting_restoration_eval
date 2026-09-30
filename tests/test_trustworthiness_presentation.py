"""Fast presentation-only checks: no large evidence table loads."""
import base64
import re
import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from restoration_eval.trustworthiness_view import book_spines, frame_crop, plaque_icon, recommendation_tag, portrait_alcove, reference_window


class PresentationTests(unittest.TestCase):
    def test_portrait_alcove_uses_exact_reference_and_shared_route(self):
        markup = portrait_alcove('data:image/png;base64,reference')
        self.assertIn('src="data:image/png;base64,reference"', markup)
        self.assertIn('?room=focused_portrait_review&amp;return_room=trustworthiness', markup)
        self.assertIn('Focused portrait review — separate study.', markup)
        self.assertIn('45 hand cases · 20 paintings.', markup)
        self.assertIn('12/12 estimates worse for hands.', markup)
        self.assertIn('10/12 significant after correction.', markup)
        self.assertIn('Rendered lightness was tested—not race or ethnicity.', markup)
        self.assertNotIn('data-action="d02"', markup)

    def test_reference_window_retains_scene_alignment(self):
        x,y,w,h = 1494,279,161,374
        markup = reference_window('reference', (x,y,w,h))
        values = {k:float(v) for k,v in re.findall(r'(width|height|left|top):(-?[\d.]+)%',markup)}
        self.assertAlmostEqual(values['width']*w/100,1672,places=6)
        self.assertAlmostEqual(values['height']*h/100,941,places=6)
        self.assertAlmostEqual(values['left']*w/100,-x,places=6)
        self.assertAlmostEqual(values['top']*h/100,-y,places=6)

    def test_recommendation_tag_keeps_record_and_reference_inspection_icon(self):
        markup = recommendation_tag('unstable candidate')
        self.assertIn('Unstable<br>candidate ·<br>inspect<br>manually', markup)
        self.assertNotIn('REVIEW ACTION', markup)
        self.assertNotIn('Read the recorded reason', markup)
        icon = base64.b64decode(re.search(r'base64,([^\"]+)', markup).group(1)).decode()
        self.assertIn('<circle', icon)
        self.assertIn('m15 15 7 7', icon)
        self.assertIn('Specialist review required', recommendation_tag('specialist review required'))
        self.assertNotIn('inspect<br>manually', recommendation_tag('specialist review required'))
        self.assertIn('&lt;record&gt;', recommendation_tag('<record>'))

    def test_book_text_and_icons_share_requested_offsets(self):
        markup = book_spines()
        self.assertEqual(markup.count('--book-shift:2px;--book-lift:-3.5px'), 1)
        self.assertEqual(markup.count('--book-shift:3px;--book-lift:-6.5px'), 3)
        self.assertEqual(markup.count('--book-lift:0px'), 1)

    def test_three_reference_button_icons(self):
        for kind in ('rules', 'policy', 'full'):
            markup = plaque_icon(kind)
            self.assertIn('aria-hidden="true"', markup)
            self.assertIn('class="trust-plaque-icon"', markup)
            encoded = re.search(r'base64,([^\"]+)', markup).group(1)
            svg = base64.b64decode(encoded).decode()
            self.assertIn('viewBox="0 0 24 24"', svg)
            self.assertIn('stroke="#392815"', svg)

    def test_portrait_landscape_square_cover_without_stretching(self):
        for box in ([230, 0, 538, 768], [0, 192, 768, 576], [0, 0, 768, 768]):
            for w,h in ((94,237),(83,224),(77,211)):
                style = frame_crop(box,w,h)
                values = {k: float(v) for k,v in re.findall(r'(width|height|left|top):(-?[\d.]+)%',style)}
                rendered_w,rendered_h = values['width']*w/100,values['height']*h/100
                self.assertAlmostEqual(rendered_w,rendered_h)
                scale = rendered_w/768
                left,top = values['left']*w/100,values['top']*h/100
                x0,y0,x1,y1 = box
                self.assertLessEqual(left+x0*scale,1e-8)
                self.assertLessEqual(top+y0*scale,1e-8)
                self.assertGreaterEqual(left+x1*scale,w-1e-8)
                self.assertGreaterEqual(top+y1*scale,h-1e-8)

    def test_five_titles_and_code_native_icons(self):
        class Parser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.images=[]
                self.text=[]
            def handle_starttag(self,tag,attrs):
                if tag=='img': self.images.append(dict(attrs))
            def handle_data(self,text): self.text.append(text)
        p=Parser()
        p.feed(book_spines())
        self.assertEqual(p.text,['Cosmos','Animal Farm','Odyssey','Gulliver’s Travels','1984'])
        self.assertEqual(len(p.images),5)
        for image in p.images:
            self.assertEqual(image['alt'],'')
            self.assertEqual(image['aria-hidden'],'true')
            svg=base64.b64decode(image['src'].split(',',1)[1]).decode()
            self.assertIn('viewBox="0 0 24 24"',svg)


if __name__=='__main__':
    unittest.main()
