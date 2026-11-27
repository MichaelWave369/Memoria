"""Fresh-process native Chroma recovery, only in newly created fixture roots."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing

from db.fixture_vector_cleanup import create_cleanup_fixture, cleanup_fixture_vector, ABSENT, PENDING
from db.fixture_vector_recovery import reopen_fixture, census, reconcile
from db.storage import store_memory, delete_memory

EXIT = 91


def seed(collection, fid, mid, *, valid=True):
    collection.upsert(ids=[str(mid)], embeddings=[[1.0,0.0,0.0]],
                      documents=["invented vector"],
                      metadatas=[{"fixture_id":fid if valid else "unrelated",
                                  "native_id":str(mid)}])


class Interrupt:
    def __init__(self, collection, boundary):
        self.collection = collection
        self.boundary = boundary

    def __getattr__(self, name):
        return getattr(self.collection, name)

    def get(self, **kwargs):
        if self.boundary == "pending":
            os._exit(EXIT)
        return self.collection.get(**kwargs)

    def delete(self, **kwargs):
        self.collection.delete(**kwargs)
        if self.boundary == "deleted":
            os._exit(EXIT)


def worker(root, action, fid, cid):
    if action == "create":
        db, client, collection, fid = create_cleanup_fixture(root)
        with closing(db):
            for text in ("target","neighbor","missing-vector","absent-forgotten","mismatch"):
                store_memory(db, {"app_name":"fixture","content":"invented "+text})
            for mid in (1,2,99):
                seed(collection,fid,mid)
            seed(collection,fid,5,valid=False)
            for mid in (1,4,5):
                delete_memory(db,mid)
            return {"fixture_id":fid,"collection_id":str(collection.id)}
    db, client, collection = reopen_fixture(root,fid,cid)
    with closing(db):
        if action in ("pending","deleted"):
            cleanup_fixture_vector(db,Interrupt(collection,action),fid,1)
            raise AssertionError("interruption did not execute")
        if action == "reconcile":
            return reconcile(db,collection,fid)
        if action == "inspect":
            return {"census":census(db,collection,fid),
                    "observations":[list(r) for r in db.execute(
                        "SELECT memory_id,state FROM fixture_vector_observations ORDER BY memory_id")],
                    "integrity":db.execute("PRAGMA integrity_check").fetchone()[0]}
        if action == "seed-stale":
            seed(collection,fid,1)
            return {"seeded":True}
        if action == "overflow":
            for mid in range(1000,1257):
                store_memory(db,{"app_name":"fixture","content":"invented budget"})
            return {"seeded":True}
        if action == "wrong-binding":
            raise AssertionError("wrong identity should fail on reopen")
        raise ValueError("unknown worker action")


@unittest.skipUnless(os.getenv("MEMORIA_NATIVE_CHROMA_FIXTURES")=="1",
                     "explicit native Chroma fixture run required")
class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/"pair"
        self.fid=self.cid=""
        created=self.run_worker("create")
        self.fid,self.cid=created["fixture_id"],created["collection_id"]

    def run_worker(self, action, *, code=0, cid=None):
        env=dict(os.environ)
        env["PYTHONPATH"]=str(Path(__file__).resolve().parents[1])
        result=subprocess.run([sys.executable,str(Path(__file__).resolve()),"--worker",
                               str(self.root),action,self.fid,self.cid if cid is None else cid],
                              env=env,capture_output=True,text=True,timeout=90)
        self.assertEqual(result.returncode,code,result.stdout+"\n"+result.stderr)
        if code==0:
            return json.loads(result.stdout.strip().splitlines()[-1])
        return result

    def assert_clean(self, report):
        after=report["after"]
        self.assertEqual(after["live_present"],[2])
        self.assertEqual(after["live_missing"],[3])
        self.assertEqual(after["forgotten_present"],[])
        self.assertEqual(after["forgotten_absent"],[1,4])
        self.assertEqual(after["unknown_orphans"],[99])
        self.assertEqual(after["binding_mismatch_count"],1)
        self.assertEqual([r["memory_id"] for r in report["receipts"]],[1,4])
        self.assertTrue(all(r["vector_observation"]==ABSENT and r["authority"]=="NONE"
                            for r in report["receipts"]))

    def test_cold_census_preserves_unknown_and_mismatch(self):
        report=self.run_worker("inspect")
        c=report["census"]
        self.assertEqual(c["live_present"],[2])
        self.assertEqual(c["live_missing"],[3])
        self.assertEqual(c["forgotten_present"],[1])
        self.assertEqual(c["forgotten_absent"],[4])
        self.assertEqual(c["unknown_orphans"],[99])
        self.assertEqual(c["binding_mismatch_count"],1)
        self.assertEqual(report["observations"],[])
        self.assertEqual(report["integrity"],"ok")
        self.assert_clean(self.run_worker("reconcile"))
        self.assertEqual(self.run_worker("inspect")["observations"],[[1,ABSENT],[4,ABSENT]])

    def test_process_exit_after_pending_before_native_delete(self):
        self.run_worker("pending",code=EXIT)
        report=self.run_worker("inspect")
        self.assertEqual(report["observations"],[[1,PENDING]])
        self.assertEqual(report["census"]["forgotten_present"],[1])
        self.assert_clean(self.run_worker("reconcile"))

    def test_process_exit_after_native_delete_before_observation(self):
        self.run_worker("deleted",code=EXIT)
        report=self.run_worker("inspect")
        self.assertEqual(report["observations"],[[1,PENDING]])
        self.assertEqual(report["census"]["forgotten_absent"],[1,4])
        self.assert_clean(self.run_worker("reconcile"))
        self.assertEqual(self.run_worker("inspect")["observations"],[[1,ABSENT],[4,ABSENT]])

    def test_reintroduced_stale_vector_is_reconciled_again(self):
        self.assert_clean(self.run_worker("reconcile"))
        self.run_worker("seed-stale")
        self.assertEqual(self.run_worker("inspect")["census"]["forgotten_present"],[1])
        self.assert_clean(self.run_worker("reconcile"))

    def test_wrong_collection_id_refused_on_cold_open(self):
        r=self.run_worker("wrong-binding",code=1,cid="00000000-0000-0000-0000-000000000000")
        self.assertIn("fixture identity mismatch",r.stderr)
        self.assertEqual(self.run_worker("inspect")["observations"],[])

    def test_budget_overflow_refuses_without_partial_cleanup(self):
        self.run_worker("overflow")
        r=self.run_worker("reconcile",code=1)
        self.assertIn("reconciliation SQL budget exceeded",r.stderr)
        import sqlite3
        with closing(sqlite3.connect(self.root/"source.db")) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM fixture_vector_observations").fetchone()[0],0)


if __name__=="__main__":
    if len(sys.argv)==6 and sys.argv[1]=="--worker":
        print(json.dumps(worker(*sys.argv[2:])))
    else:
        unittest.main()
