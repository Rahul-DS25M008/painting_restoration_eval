"""Scientific and state-contract checks for the 49 public inspection pairs."""
import json
import sys
import unittest
from unittest.mock import patch
from pathlib import Path
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'tools'))
from restoration_eval.metric_inspection import public_contract,resolve_pair,LENSES,REGIONS
from restoration_eval.metric_inspection_view import load_inspection
from build_metric_inspection import aligned,regions_for,unletterbox,patch_field,seam_difference,patch_assignment


class InspectionPolicyTests(unittest.TestCase):
    def test_all_49_pairs_have_explicit_roles(self):
        pairs=public_contract()
        self.assertEqual(len(pairs),49)
        self.assertEqual(sum(x['allowed'] for x in pairs.values()),37)
        for lens in ('structure','perceptual','features','semantic'):
            for region in ('damaged','boundary','outside'):
                spec=resolve_pair(lens,region)
                self.assertFalse(spec['allowed'])
                self.assertIn('rectangular',spec['reason'])
                self.assertNotIn('recipe',spec)

    def test_named_submeasure_is_region_specific(self):
        self.assertEqual(resolve_pair('local','boundary')['recipe'],'seam')
        self.assertEqual(resolve_pair('local','damaged')['recipe'],'colour')
        self.assertEqual(resolve_pair('local','crop')['recipe'],'texture')
        self.assertEqual(resolve_pair('spatial','damaged')['recipe'],'improvement')
        self.assertEqual(resolve_pair('spatial','outside')['recipe'],'change')
        self.assertEqual(resolve_pair('semantic','patches')['role'],'primary')
        with self.assertRaises(ValueError):resolve_pair('lpips','mask')

    def test_spatial_supports_are_canonical_and_distinct(self):
        mask=np.zeros((768,768),bool);mask[200:300,250:350]=True
        regions,patches=regions_for(mask.shape,(40,20,720,740),mask)
        self.assertEqual(regions['damaged'].pixel_count,10000)
        self.assertEqual(regions['crop'].bbox,(242,192,358,308))
        self.assertFalse(np.any(regions['outside'].mask & mask))
        self.assertTrue(np.all(regions['boundary'].mask <= regions['content'].mask))
        for p in patches:
            self.assertEqual((p.width,p.height),(224,224))
            self.assertGreaterEqual(np.mean(regions['content'].mask[p.y_min:p.y_max,p.x_min:p.x_max]),.5)

    def test_projection_never_stretches_into_another_region(self):
        result=aligned(np.ones((4,4)),(10,20,30,40),(50,50),nearest=True)
        self.assertTrue(np.isnan(result[:20]).all())
        self.assertTrue(np.all(result[20:40,10:30]==1))
        self.assertEqual(np.isfinite(result).sum(),400)
        wide=unletterbox(np.ones((7,7)),400,200)
        self.assertEqual(wide.shape,(112,224))

    def test_patch_display_uses_real_scores_without_blurring(self):
        mask=np.zeros((256,512),bool);mask[100:110,100:110]=True
        _,patches=regions_for(mask.shape,(0,0,512,256),mask)
        values=list(range(len(patches)))
        field=patch_field(values,patches,mask.shape)
        self.assertTrue(set(np.unique(field[np.isfinite(field)])) <= set(values))

    def test_seam_uses_the_existing_normalized_gradient_convention(self):
        from restoration_eval.local_consistency import _gradient
        from skimage.color import rgb2gray
        ref=np.zeros((32,32,3),np.uint8)
        out=ref.copy();out[8:24,8:24]=255
        expected=np.abs(_gradient(rgb2gray(ref))[0]-_gradient(rgb2gray(out))[0])
        np.testing.assert_allclose(seam_difference(ref,out),expected,atol=1e-7)

    def test_shared_patch_assignment_matches_dense_nearest_windows(self):
        mask=np.zeros((256,512),bool)
        _,patches=regions_for(mask.shape,(0,0,512,256),mask)
        owners,support=patch_assignment(patches,mask.shape)
        yy,xx=np.indices(mask.shape)
        centres=np.array([((p.x_min+p.x_max)/2,(p.y_min+p.y_max)/2) for p in patches])
        expected=np.argmin((xx[...,None]-centres[:,0])**2+(yy[...,None]-centres[:,1])**2,axis=-1)
        np.testing.assert_array_equal(owners,expected)
        np.testing.assert_array_equal(support,np.logical_or.reduce([p.mask for p in patches]))


class InspectionExhibitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta=load_inspection(ROOT,'p018')
        cls.folder=ROOT/'streamlit_assets/evidence/metric_framework/p018'

    def test_every_enabled_pair_has_aligned_evidence_and_nonempty_support(self):
        m=self.meta
        self.assertEqual(m['candidate_id'],'candidate__lama__canonical__p018__mixed_damage__c00')
        with np.load(self.folder/'numeric.npz') as numeric:
            for key,spec in m['pairs'].items():
                with self.subTest(pair=key):
                    if not spec['allowed']:
                        self.assertNotIn('maps',spec);continue
                    mask=np.asarray(Image.open(ROOT/m['regions'][spec['region']]['path']))>=128
                    for name in spec['maps']:
                        a=numeric[name].astype(np.float32)
                        self.assertEqual(tuple(a.shape),tuple(m['shape']))
                        self.assertTrue(np.isfinite(a[mask]).any())
                        self.assertTrue(np.isfinite(spec['summary'][0]['mean']))
                        with Image.open(ROOT/m['assets'][name]['path']) as image:
                            self.assertEqual(image.size,tuple(reversed(m['shape'])))

    def test_pixel_and_improvement_arithmetic_matches_source_images(self):
        m=self.meta
        arrays={k:np.asarray(Image.open(ROOT/v['path']).convert('RGB'),np.float32)/255 for k,v in m['sources'].items() if k!='mask'}
        expected=np.abs(arrays['reference']-arrays['restored']).mean(-1)
        improvement=np.abs(arrays['reference']-arrays['damaged']).mean(-1)-expected
        with np.load(self.folder/'numeric.npz') as numeric:
            np.testing.assert_allclose(numeric['pixel'],expected,atol=.0005)
            np.testing.assert_allclose(numeric['improvement'],improvement,atol=.0005)

    def test_invalid_identity_is_rejected(self):
        with self.assertRaises(ValueError):load_inspection(ROOT,'../p018')

    def test_content_geometry_and_sources_are_pinned(self):
        import hashlib
        m=self.meta
        self.assertEqual(m['loader_version'],'metric_view.v2')
        with Image.open(ROOT/m['regions']['content']['path']) as support:
            self.assertEqual(m['content_bbox'],list(support.getbbox()))
        for item in m['sources'].values():
            self.assertEqual(hashlib.sha256((ROOT/item['path']).read_bytes()).hexdigest(),item['sha256'])

    def test_mismatched_recipe_is_rejected_without_fallback(self):
        meta=json.loads((self.folder/'manifest.json').read_text(encoding='utf-8'))
        meta['pairs']['pixel:whole']['recipe']='improvement'
        with patch.object(Path,'read_text',return_value=json.dumps(meta)):
            with self.assertRaisesRegex(ValueError,'recipe mismatch'):
                load_inspection(ROOT,'p018')

    def test_changed_source_is_rejected_without_fallback(self):
        meta=json.loads((self.folder/'manifest.json').read_text(encoding='utf-8'))
        meta['sources']['reference']['sha256']='0'*64
        with patch.object(Path,'read_text',return_value=json.dumps(meta)):
            with self.assertRaisesRegex(ValueError,'source changed'):
                load_inspection(ROOT,'p018')

    def test_changed_map_is_rejected_without_fallback(self):
        meta=json.loads((self.folder/'manifest.json').read_text(encoding='utf-8'))
        meta['assets']['pixel']['sha256']='0'*64
        with patch.object(Path,'read_text',return_value=json.dumps(meta)):
            with self.assertRaisesRegex(ValueError,'checksum mismatch'):
                load_inspection(ROOT,'p018')


class InspectionControllerTests(unittest.TestCase):
    def test_requested_region_icons_keep_grayscale_painting_detail(self):
        source=(ROOT/'streamlit_app.py').read_text(encoding='utf-8')
        targets=':is([data-region="content"],[data-region="crop"],[data-region="outside"],[data-region="patches"])'
        self.assertIn(targets+' .metric-region-icon { filter:grayscale(1); }',source)
        self.assertIn(targets+' .metric-region-mask { mix-blend-mode:multiply; opacity:.48; filter:grayscale(1); }',source)

    def test_arrakis_art_and_surprise_tooltip_cleanup_are_decorative(self):
        source=(ROOT/'streamlit_app.py').read_text(encoding='utf-8')
        self.assertIn('class="metric-arrakis-art"',source)
        self.assertIn('transform:skewY(-16deg)',source)
        self.assertNotIn('help="Advance to another registered painting',source)
        self.assertIn('on_click=advance_metric_painting',source)
        self.assertTrue((ROOT/'streamlit_assets/ornaments/arrakis_desert.png').is_file())

    def test_cabinet_paper_angles_and_label_offset_are_scoped(self):
        source=(ROOT/'streamlit_app.py').read_text(encoding='utf-8')
        self.assertIn('transform:translateY(.18cqw) rotate(-1.1deg)',source)
        self.assertIn('.metric-lens.active .lens-label { transform:translateY(.18cqw)',source)
        self.assertIn('class="metric-plaque-mount"><div class="metric-plaque-sheet"><section class="metric-plaque"',source)
        self.assertIn('transform:skewY(-2deg); transform-origin:top right;',source)
        self.assertIn('top:-.22cqw; height:.24cqw; background:#38281b',source)
        self.assertIn('transform:skewY(-1.1deg)',source)

    def test_cabinet_icons_and_conservation_study_are_scoped(self):
        source=(ROOT/'streamlit_app.py').read_text(encoding='utf-8')
        self.assertIn('.metric-lens.active .glyph { transform:translateY(.18cqw); }',source)
        self.assertIn('transform:skewY(-2.6deg)',source)
        self.assertNotIn('transform:skewY(.35deg)',source)
        self.assertIn('class="metric-conservation-study"',source)
        import xml.etree.ElementTree as ET
        study=ET.parse(ROOT/'streamlit_assets/ornaments/conservation_study.svg').getroot()
        self.assertEqual(study.attrib['viewBox'],'0 0 60 300')

    def test_dune_binding_is_decorative_and_perspective_aligned(self):
        source=(ROOT/'streamlit_app.py').read_text(encoding='utf-8')
        self.assertIn('class="metric-dune-cover"',source)
        self.assertIn('transform:skewY(14deg) skewX(-1.5deg)',source)
        import xml.etree.ElementTree as ET
        cover=ET.parse(ROOT/'streamlit_assets/ornaments/dune_archive_cover.svg').getroot()
        self.assertEqual(cover.attrib['viewBox'],'0 0 140 118')
        self.assertIn('DUNE',''.join(cover.itertext()))

    def test_cabinet_reuses_shell_drawers_and_reference_style_icons(self):
        source=(ROOT/'streamlit_app.py').read_text(encoding='utf-8')
        self.assertIn('Source rectangles: closed (1318,146,259,48), open (1318,335,259,138)',source)
        self.assertIn("background-image: url('{shell_uri}')",source)
        self.assertIn('lens_icon_paths = {',source)
        self.assertIn('class="lens-label"',source)
        self.assertNotIn('lens_glyphs =',source)
        self.assertNotIn('border:.09cqw solid #b98a3b',source)

    def test_region_icons_and_plaque_content_are_scoped_and_contained(self):
        source=(ROOT/'streamlit_app.py').read_text(encoding='utf-8')
        controller=(ROOT/'streamlit_assets/metric_controller.js').read_text(encoding='utf-8')
        self.assertIn('class="metric-region-mask"',source)
        self.assertIn('evidence["regions"][key]["uri"]',source)
        self.assertNotIn('border-bottom:.06cqw solid #82684c66',source)
        self.assertIn('overscroll-behavior:contain',source)
        self.assertIn("directionNode(spec.direction)",controller)
        self.assertIn("textNode('summary','Measurements & support')",controller)
        self.assertIn("doc.createTextNode(part)",controller)
        self.assertNotIn('innerHTML',controller)

    def test_second_cosmetic_batch_is_scoped_to_metric_room(self):
        source=(ROOT/'streamlit_app.py').read_text(encoding='utf-8')
        self.assertIn('.metric-stage .museum-nav a { text-decoration:none !important;',source)
        self.assertIn('class="metric-ledger-page"',source)
        self.assertIn('class="metric-ledger-leaf"',source)
        self.assertIn('transform:rotate(3deg) skewX(1deg)',source)
        import xml.etree.ElementTree as ET
        leaf=ET.parse(ROOT/'streamlit_assets/ornaments/ledger_botanical.svg').getroot()
        self.assertEqual(leaf.attrib['viewBox'],'0 0 120 100')

    def test_full_canvas_framing_is_independent_of_selected_region(self):
        source=(ROOT/'streamlit_assets/metric_controller.js').read_text(encoding='utf-8')
        geometry=source.split('function geometry() {',1)[1].split('function anchorControls()',1)[0]
        self.assertIn('bounds=[0,0,payload.shape[1],payload.shape[0]]',geometry)
        self.assertIn('w:frame.width,h:frame.height,left:0,top:0',geometry)
        self.assertNotIn('state.region',geometry)
        self.assertNotIn('contentBbox',geometry)
        self.assertIn("readout,textNode('p',spec.calculation)",source)

    def test_metric_cosmetics_use_shell_plates_and_scoped_dropdown(self):
        source=(ROOT/'streamlit_app.py').read_text(encoding='utf-8')
        self.assertIn('body:has(.metric-stage) [data-testid="stSelectboxVirtualDropdown"]:has([aria-label="Change painting"])',source)
        self.assertIn('.metric-painting > img { object-fit:fill; }',source)
        self.assertIn('display:grid; place-items:center; padding:.25cqw .8cqw;',source)
        self.assertNotIn('.metric-loupe-readout { position:absolute;',source)

    def test_controller_has_fail_closed_state_and_patch_geometry(self):
        source=(ROOT/'streamlit_assets/metric_controller.js').read_text(encoding='utf-8')
        for token in ("request!==generation", "state.region=null", "awaiting-region", "patchOutline.dataset.window", "setPointerCapture", "ArrowRight"):
            self.assertIn(token,source)
        for forbidden in ("location.reload", "location.href", "fetch("):
            self.assertNotIn(forbidden,source)


if __name__=='__main__':unittest.main()
