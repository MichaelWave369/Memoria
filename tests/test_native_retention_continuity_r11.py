"""Cold fixture restores compared with an independently retained advisory pin."""
from contextlib import closing
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from db.fixture_vector_cleanup import create_cleanup_fixture, cleanup_fixture_vector
from db.fixture_vector_recovery import reopen_fixture
from db.fixture_retention_continuity import snapshot, compare
from db.storage import store_memory, delete_memory

KEY = b"r"*32  # public disposable fixture key, never production material


def worker(root, action, fid, cid):
    if action=="create":
        db,client,collection,fid=create_cleanup_fixture(root)
        with closing(db):
            for text in ("target","neighbor"):
                mid=store_memory(db,{"app_name":"fixture","content":"invented "+text})
                collection.upsert(ids=[str(mid)],embeddings=[[1.0,0.0,0.0]],
                    documents=["invented vector"],metadatas=[{"fixture_id":fid,"native_id":str(mid)}])
            return {"fixture_id":fid,"collection_id":str(collection.id),
                    "snapshot":snapshot(db,collection,fid,KEY)}
    db,client,collection=reopen_fixture(root,fid,cid)
    with closing(db):
        if action=="forget":
            delete_memory(db,1)
            cleanup_fixture_vector(db,collection,fid,1)
        elif action=="edit":
            db.execute("UPDATE memories SET content='different invented text' WHERE id=2")
            db.commit()
        elif action=="mismatch":
            collection.upsert(ids=["2"],embeddings=[[1.0,0.0,0.0]],
                metadatas=[{"fixture_id":"wrong","native_id":"2"}])
        elif action not in ("inspect","wrong-key"):
            raise ValueError("unknown worker operation")
        return snapshot(db,collection,fid,b"x"*32 if action=="wrong-key" else KEY)


@unittest.skipUnless(os.getenv("MEMORIA_NATIVE_CHROMA_FIXTURES")=="1",
                     "explicit native Chroma fixture run required")
class RetentionContinuityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/"pair"
        self.old=Path(self.tmp.name)/"old-pair"
        self.fid=self.cid=""
        initial=self.run_worker("create")
        self.fid,self.cid=initial["fixture_id"],initial["collection_id"]
        self.initial=initial["snapshot"]
        # Every copy occurs after the owning worker has exited.
        shutil.copytree(self.root,self.old)
        self.latest=self.run_worker("forget")
        self.pin=self.latest["witness_sha256"]
        self.assertNotEqual(self.initial,self.latest)

    def run_worker(self,action,code=0):
        env=dict(os.environ)
        env["PYTHONPATH"]=str(Path(__file__).resolve().parents[1])
        result=subprocess.run([sys.executable,str(Path(__file__).resolve()),"--worker",
                               str(self.root),action,self.fid,self.cid],
                              env=env,capture_output=True,text=True,timeout=90)
        self.assertEqual(result.returncode,code,result.stdout+"\n"+result.stderr)
        return json.loads(result.stdout.strip().splitlines()[-1]) if code==0 else result

    def test_fresh_snapshot_matches_latest_and_wrong_key_does_not(self):
        self.assertEqual(self.run_worker("inspect"),self.latest)
        self.assertEqual(compare(self.latest,self.pin),
                         {"matches":True,"authority":"NONE","status":"HELD"})
        self.assertFalse(compare(self.run_worker("wrong-key"),self.pin)["matches"])

    def test_complete_pair_restore_detected_by_retained_pin(self):
        shutil.rmtree(self.root)
        shutil.copytree(self.old,self.root)
        restored=self.run_worker("inspect")
        self.assertEqual(restored,self.initial)
        self.assertFalse(compare(restored,self.pin)["matches"])
        # If the separately retained pin also rolls back, equality alone
        # cannot establish freshness. Preserve this negative control.
        self.assertTrue(compare(restored,self.initial["witness_sha256"])["matches"])

    def test_primary_only_restore_changes_retention_topology(self):
        shutil.copyfile(self.old/"source.db",self.root/"source.db")
        self.assertFalse(compare(self.run_worker("inspect"),self.pin)["matches"])

    def test_vector_only_restore_changes_retention_topology(self):
        shutil.rmtree(self.root/"chroma")
        shutil.copytree(self.old/"chroma",self.root/"chroma")
        self.assertFalse(compare(self.run_worker("inspect"),self.pin)["matches"])

    def test_content_change_outside_retention_contract(self):
        # This is intentionally NOT full content integrity.
        self.assertEqual(self.run_worker("edit"),self.latest)

    def test_mismatched_binding_refused(self):
        r=self.run_worker("mismatch",code=1)
        self.assertIn("unqualified vector binding",r.stderr)

    @unittest.skipUnless(os.getenv("MEMORIA_NATIVE_PHI_MEMORY") and
                         os.getenv("MEMORIA_NATIVE_POCKETMESH"),
                         "explicit pinned upstream anchor checkouts required")
    def test_reuse_native_phimemory_pocketmesh_anchor(self):
        shutil.rmtree(self.root)
        shutil.copytree(self.old,self.root)
        restored=self.run_worker("inspect")
        self.assertEqual(restored,self.initial)
        script=Path(os.environ["MEMORIA_NATIVE_PHI_MEMORY"])/"scripts/living_native_continuity.mjs"
        result=subprocess.run(["node",str(script),os.environ["MEMORIA_NATIVE_POCKETMESH"],
                               restored["witness_sha256"],self.pin],
                              capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+"\n"+result.stderr)
        report=json.loads(result.stdout.strip().splitlines()[-1])
        self.assertEqual(report["checks_passed"],9)
        self.assertEqual(report["status"],"HELD")
        self.assertEqual(report["authority"],"NONE")


if __name__=="__main__":
    if len(sys.argv)==6 and sys.argv[1]=="--worker":
        print(json.dumps(worker(*sys.argv[2:])))
    else:
        unittest.main()
