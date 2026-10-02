"""Bounded Archive step-3 checks; never execute scientific producers."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from collections import Counter

from restoration_eval import research_archive as archive
from restoration_eval.dashboard_application import open_dashboard_package
from restoration_eval.research_archive_view import room_markup, reference_window
from restoration_eval.room_runtime import navigation_query


class ResearchArchiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.package=open_dashboard_package(archive.ROOT)
        cls.data=archive.payload(cls.package)

    def test_exact_stage_scope_and_default_record(self):
        stages={r['id'] for r in self.data['stages']}
        self.assertEqual(stages,{f'N{i:02}' for i in range(1,34)}|{'N12A','D01','D02'})
        self.assertEqual(self.data['record']['summary']['id'],'N33')
        self.assertTrue(self.data['record']['run']['git_dirty'])
        self.assertEqual(self.data['record']['run']['run_id'],'run_aef04267c2e44495a4e7a6249426bd4d')

    def test_n33_upstream_identity_is_not_augmented(self):
        upstream=self.data['record']['run']['dataset_versions']['upstream_run_ids']
        self.assertEqual(set(upstream),{f'{i:02}' for i in range(1,33)})
        for key,run_id in upstream.items():
            self.assertEqual(archive.record(self.package,'N'+key)['run']['run_id'],run_id)
        self.assertIn('controlled_50',archive.record(self.package,'D01')['summary']['scope'])

    def test_report_populations_stay_separate(self):
        self.assertEqual(Counter(r['report_type'] for r in self.data['reports']),{'painting':300,'case':30,'collection':1,'model':5,'final':1})

    def test_provenance_and_missingness(self):
        paintings=self.data['paintings']
        self.assertEqual(len(paintings),300)
        self.assertTrue(all(p['source_url'] and p['rights_status'] and len(p['raw_sha256'])==64 for p in paintings))
        for field in ('style_or_period','date_or_period','medium'):
            self.assertEqual(sum(bool(p[field]) for p in paintings),268)

    def test_claim_limit_figure_and_check_counts(self):
        self.assertEqual((len(self.data['claims']),len(self.data['limitations']),len(self.data['figures'])),(49,18,24))
        self.assertEqual({r['group'] for r in self.data['limitations']},{'Dataset','Models','Interpretation','Use'})
        self.assertEqual(len({r['table_row_id'] for r in self.data['limitations']}),18)
        self.assertEqual(self.data['checks'],{'total':536,'passed':536})

    def test_publications_are_lazy_and_pinned(self):
        self.assertEqual(self.data['publications'],[])
        rows=archive.payload(self.package,view='publications')['publications']
        self.assertEqual(len(rows),2653)
        self.assertEqual(Counter(r['storage_tier'] for r in rows),{'candidates':2644,'diagnostics':9})
        self.assertEqual(len(archive.payload(self.package,view='publications_diagnostics')['publications']),2653)
        self.assertTrue(all(len(r['pinned_revision'])==40 and '/resolve/main/' not in r['pinned_url'] for r in rows))
        self.assertEqual(len(self.data['bundles']),6)
        self.assertEqual(self.data['n32_package']['objects'],361)

    def test_one_painting_partition_only(self):
        with patch.object(type(self.package),'load_painting',side_effect=self.package.load_painting) as load:
            data=archive.payload(self.package,view='candidates',painting='p018')
        load.assert_called_once_with('p018')
        self.assertTrue(data['candidate_rows'])
        self.assertTrue(all(r['painting_id']=='p018' for r in data['candidate_rows']))

    def test_invalid_selections_never_fall_back(self):
        for identity in ('N34','N35','N37','../N33','D03'):
            with self.assertRaises(ValueError): archive.record(self.package,identity)
        with self.assertRaises(ValueError): archive.payload(self.package,view='unknown')
        with self.assertRaises(ValueError): archive.payload(self.package,painting='p999')
        with self.assertRaises(ValueError): archive.selected_file(self.package,'N33','../../config.yaml')

    def test_saved_manifest_verification_and_discrepancy(self):
        self.assertEqual(archive.verify_manifest(self.package,'N33')['state'],'verified')
        n29=archive.record(self.package,'N29')['summary']
        self.assertEqual(n29['artifact_manifest_state'],'recorded_hash_mismatch')
        self.assertNotEqual(n29['artifact_manifest_expected_sha256'],n29['artifact_manifest_observed_sha256'])

    def test_exact_figure_bytes_verified(self):
        figure=self.data['figures'][0]
        raw,_=archive.selected_file(self.package,'N33',figure['path'])
        self.assertEqual(hashlib.sha256(raw).hexdigest(),figure['sha256'])

    def test_corrupt_selected_file_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'record.json').write_bytes(b'bad')
            with patch.object(archive,'ROOT',root),patch.object(archive,'record',return_value={'files':[{'path':'record.json','size_bytes':3,'sha256':'0'*64}]}):
                with self.assertRaisesRegex(ValueError,'checksum mismatch'):
                    archive.selected_file(self.package,'N33','record.json')

    def test_collections_and_large_files_are_not_materialized(self):
        for item in ({'path':'collection','directory':True,'size_bytes':5}, {'path':'large','size_bytes':33*1024*1024}):
            with patch.object(archive,'record',return_value={'files':[item]}):
                with self.assertRaises(ValueError): archive.selected_file(self.package,'N33',item['path'])

    def test_all_partitions_check_their_saved_hash(self):
        manifest=json.loads((archive.INDEX/'manifest.json').read_text())
        self.assertLess(sum(r['size_bytes'] for r in manifest['partitions'].values()),5*1024*1024)
        for name in manifest['partitions']: self.assertIsNotNone(archive.partition(name))

    def test_markup_and_navigation_contract(self):
        markup=room_markup(self.data,'<nav>Existing navigation</nav>','shell.png')
        self.assertIn('Trace every conclusion to its saved evidence.',markup)
        self.assertIn('536 / 536',markup)
        self.assertNotIn('recorded as dirty',markup)
        self.assertIn(self.data['record']['summary']['run_id'],markup)
        self.assertIn(self.data['record']['summary']['git_commit'],markup)
        self.assertNotIn('planned after',markup)
        self.assertIn('Zenodo published',markup)
        self.assertIn('10.5281/zenodo.23092185',markup)
        self.assertIn('ra-zenodo-published',markup)
        self.assertEqual(markup.count('data-action="final_sources"'),2)
        query={'room':'research_archive','ar_record':'N33','ar_view':'record'}
        self.assertEqual(navigation_query({'room':'research_archive','query':query},'research_archive'),query)

    def test_lettering_is_the_original_reference_not_regenerated(self):
        source=archive.ROOT/'docs/dashboard_design_finalists/approved_current/11_research_archive_final.png'
        asset=archive.ROOT/'streamlit_assets/rooms/research_archive_lettering.png'
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),hashlib.sha256(asset.read_bytes()).hexdigest())
        markup=room_markup(self.data,'<nav>Navigation</nav>','shell.png','lettering.png')
        self.assertIn('class="ra-lettering-source" src="lettering.png"',markup)
        self.assertGreater(markup.count('ra-reference-window'),30)
        for action in ['search','paintings','cases','candidates','reports','models','runs','checksums','figures','claims','limits:Dataset','limits:Models','limits:Interpretation','limits:Use','publications:candidates','publications:diagnostics','zenodo','final_report','verify']:
            self.assertIn(f'data-action="{action}"',markup)
        self.assertIn('background-position:',reference_window((532,58,620,125)))

    def test_reference_counts_match_the_frozen_archive(self):
        population=self.data['population']
        for key,expected in [('painting_count',300),('registered_case_count',3425),('indexed_inspectable_candidate_count',13879),('n32_browsable_record_count',331),('model_report_count',5)]:
            self.assertEqual(population[key],expected)
        self.assertEqual(self.data['individual_publications'],2653)

    def test_decorative_portraits_preserve_controls_and_are_local(self):
        portraits={name:f'{name}.png' for name in ('azhdaha','leto_ii','dragon')}
        plain=room_markup(self.data,'<nav>Navigation</nav>','shell.png','lettering.png')
        decorated=room_markup(self.data,'<nav>Navigation</nav>','shell.png','lettering.png',portraits)
        self.assertEqual(decorated.count('data-action='),plain.count('data-action='))
        self.assertEqual(decorated.count('aria-hidden="true" draggable="false"'),3)
        for name in portraits:
            self.assertIn(f'ra-portrait-{name}',decorated)
            self.assertTrue((archive.ROOT/'streamlit_assets/rooms/archive_portraits'/f'{name}.png').is_file())
        css=(archive.ROOT/'streamlit_assets/research_archive.css').read_text()
        self.assertIn('mix-blend-mode:multiply',css)
        self.assertIn('font:700 .91cqw',css)

    def test_publication_receipt_is_separate_from_frozen_partitions(self):
        z=self.data['zenodo']
        self.assertEqual(z['status'],'published')
        self.assertEqual(z['doi'],'10.5281/zenodo.23092185')
        self.assertEqual(len(z['files']),15)
        self.assertEqual(sum(f['size_bytes'] for f in z['files']),40565606666)
        self.assertEqual(len([f for f in z['files'] if '.zip.00' in f['name']]),8)
        self.assertNotIn('zenodo',archive.catalogue(self.package))
        self.assertNotIn('?token=',json.dumps(z))


if __name__=='__main__': unittest.main()
