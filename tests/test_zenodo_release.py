"""Small offline regression tests for the publication-only release builder."""
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path

SPEC=importlib.util.spec_from_file_location('zenodo_builder',Path(__file__).parents[1]/'tools/build_zenodo_release.py')
mod=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class ZenodoReleaseTests(unittest.TestCase):
    def test_published_release_cannot_be_rebuilt(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            plan=root/mod.PLAN
            plan.parent.mkdir(parents=True)
            plan.write_text(json.dumps({'release_status':'published'}))
            for preflight in (True,False):
                with self.assertRaisesRegex(ValueError,'already published'):
                    mod.build(root,preflight)

    def test_pinned_revision_comes_from_existing_commit(self):
        commit='a'*40
        row={'repository_id':'owner/dataset','publication_commit_url':f'https://huggingface.co/datasets/owner/dataset/commit/{commit}','sha256':'b'*64,'publication_status':'published_verified','verification_status':'verified','revision':'main','path_in_repository':'images/p001.png','artifact_id':'one','local_relative_path':'outputs/p001.png','size_bytes':'123','verified_at_utc':'2026-09-01'}
        result=mod.pinned_artifact(row)
        self.assertEqual(result['revision'],commit)
        self.assertNotIn('/main/',result['pinned_url'])
        row['publication_commit_url']='https://other.invalid/commit/'+commit
        with self.assertRaises(ValueError): mod.pinned_artifact(row)

    def test_path_escape_and_pointer_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            with self.assertRaises(ValueError): mod.checked_path(root,'../secret')
            (root/'pointer').write_bytes(b'version https://git-lfs.github.com/spec/v1\n')
            with self.assertRaises(ValueError): mod.file_record(root,'pointer')

    def test_archive_roundtrip_retains_exact_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); (root/'example.txt').write_bytes(b'unchanged\r\nbytes\n')
            record=mod.file_record(root,'example.txt')
            target=root/'release.zip'
            entries=mod.write_zip(root,target,[record],{'generated.json':b'{}'})
            self.assertEqual(len(entries),2)
            mod.verify_zip(target,entries)
            entries[0]['sha256']='0'*64
            with self.assertRaises(ValueError): mod.verify_zip(target,entries)

    def test_source_keeps_assets_but_excludes_private_and_obsolete_files(self):
        plan={'source_root_files':['README.md'],'required_source_files':['LICENSE'],
              'exclude_prefixes':['docs/thesis/'], 'exclude_files':['docs/supervisor/Next_Steps.pdf']}
        selected=mod.select_source(['notebooks/01.ipynb','notebooks/.ipynb_checkpoints/01.ipynb','src/module.py','streamlit_assets/room.png','docs/thesis/draft.docx','docs/supervisor/Next_Steps.pdf','.codex_tmp/bundle.zip'],plan)
        self.assertEqual(selected,['LICENSE','README.md','notebooks/01.ipynb','src/module.py','streamlit_assets/room.png'])

    def test_streaming_full_and_partial_hashes_differ(self):
        data = b'a' * (1024*1024) + b'b' * 17
        digest, size, prefix = mod.digest_stream(io.BytesIO(data), 'map.bin', prefix_bytes=1024*1024)
        self.assertEqual(digest, mod.sha(data))
        self.assertEqual(size, len(data))
        self.assertEqual(prefix, mod.sha(data[:1024*1024]))
        self.assertNotEqual(prefix, digest)

    def test_changed_inventory_digest_blocks_build(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); (root/'map.bin').write_bytes(b'abc')
            record={'path':'map.bin','size_bytes':3,'hash_bytes':3,'inventory_hash':'0'*64}
            with self.assertRaises(ValueError): mod.write_zip(root, root/'bad.zip', [record])

    def test_stream_rejects_token_crossing_chunk_boundary(self):
        data=b' '*(1024*1024-3)+b'hf_'+b'x'*35
        with self.assertRaises(ValueError): mod.digest_stream(io.BytesIO(data), 'config.txt')


if __name__=='__main__': unittest.main()
