"""Synthetic native export qualification with the unchanged PhiMemory9 intake."""
from contextlib import closing
from pathlib import Path
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from db.fixture_qualification import handoff, commitment, AUDITED_BASE, BLOCKERS
from db.genomememory_export import create_fixture, SOURCE_REVISION
from db.storage import store_memory, set_permission


class FixtureQualificationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.conn = create_fixture(Path(self.tmp.name)/"fixture.db", "fixture:qualification")
        self.addCleanup(self.conn.close)
        self.mid = store_memory(self.conn, dict(app_name="demo", content="invented payload",
            agent_id="fixture:author", timestamp="2026-06-20T12:00:00+00:00",
            tags=["research"], importance_score=1, metadata={"private":"not exported"}))
        store_memory(self.conn, dict(app_name="other", content="invented other",
            agent_id="fixture:other", tags=["other"]))
        set_permission(self.conn,"demo",True,False)

    def export(self, **kwargs):
        return handoff(self.conn, **({"expected_app":"demo","fixture_id":"fixture:qualification"} | kwargs))

    def test_held_contract_and_metadata_only_scope(self):
        result = self.export()
        self.assertEqual(result["status"],"HELD")
        self.assertFalse(result["live_ready"])
        self.assertEqual(result["authority"],"NONE")
        self.assertEqual(result["audited_base"],AUDITED_BASE)
        self.assertEqual(result["legacy_adapter_revision"],SOURCE_REVISION)
        self.assertNotEqual(AUDITED_BASE,SOURCE_REVISION)
        self.assertEqual(result["blockers"],list(BLOCKERS))
        self.assertEqual(result["snapshot_sha256"],commitment(result["snapshot"]))
        self.assertEqual([row["id"] for row in result["snapshot"]["rows"]],[self.mid])
        self.assertNotIn("invented payload",json.dumps(result))
        self.assertNotIn("not exported",json.dumps(result))

    def test_permission_and_fixture_refusal(self):
        with self.assertRaises(PermissionError):
            self.export(expected_app="other")
        with self.assertRaises(PermissionError):
            self.export(fixture_id="fixture:wrong")
        set_permission(self.conn,"demo",False,True)
        with self.assertRaises(PermissionError):
            self.export()

    def test_read_only_and_stable_commitment(self):
        before=tuple(self.conn.iterdump())
        self.assertEqual(self.export(),self.export())
        self.assertEqual(tuple(self.conn.iterdump()),before)
        self.assertFalse(self.conn.in_transaction)

    def test_metadata_edit_changes_commitment(self):
        before=self.export()
        self.conn.execute("UPDATE memories SET tags=? WHERE id=?",
                          ('["changed"]',self.mid))
        self.conn.commit()
        self.assertNotEqual(self.export()["snapshot_sha256"],before["snapshot_sha256"])

    def test_caller_transaction_not_committed(self):
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            with self.assertRaisesRegex(ValueError,"independent"):
                self.export()
            self.assertTrue(self.conn.in_transaction)
        finally:
            self.conn.rollback()

    def test_empty_scope_and_budget_refusal(self):
        self.conn.execute("DELETE FROM memories WHERE id=?",(self.mid,))
        self.conn.commit()
        with self.assertRaises(ValueError):
            self.export()
        with self.assertRaisesRegex(ValueError,"byte budget"):
            commitment({"fixture":"x"*(1024*1024)})

    @unittest.skipUnless(os.getenv("MEMORIA_NATIVE_PHI_MEMORY"),
                         "pinned PhiMemory9 checkout required")
    def test_actual_upstream_adapter_stages_held(self):
        result=self.export()
        env=dict(os.environ)
        env["PYTHONPATH"]=str(Path(env["MEMORIA_NATIVE_PHI_MEMORY"])/"src")
        code="""import json,sys
from phimemory9.genomememory_memoria import review_snapshot,stage_snapshot
s=json.load(sys.stdin)
r=review_snapshot(s,'demo')
stage=stage_snapshot(s,'demo',r['snapshot_sha256'])
assert stage['eligible_count']==0 and stage['authority']=='NONE'
assert len(stage['candidates'])==1
assert stage['candidates'][0]['status']=='HELD'
assert all(v is None for v in stage['candidates'][0]['policy'].values())
print('native-held-ok')
"""
        proc=subprocess.run([sys.executable,"-c",code],env=env,
                            input=json.dumps(result["snapshot"]),capture_output=True,text=True,timeout=30)
        self.assertEqual(proc.returncode,0,proc.stderr)
        self.assertEqual(proc.stdout.strip(),"native-held-ok")


if __name__=="__main__":
    unittest.main()
