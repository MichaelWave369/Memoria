"""Opt-in native Chroma integration tests. All paths and payloads disposable."""
from pathlib import Path
import os
import sqlite3
import tempfile
import unittest

from db.fixture_vector_cleanup import (
    create_cleanup_fixture, cleanup_fixture_vector, ABSENT, PENDING, SCHEMA,
)
from db.storage import delete_memory, store_memory


class FaultCollection:
    """Inject a failure at a native collection boundary, preserving binding."""
    def __init__(self, collection, *, noop=False, fail_after=False):
        self.collection = collection
        self.noop = noop
        self.fail_after = fail_after
        self.deletes = 0

    def __getattr__(self, name):
        return getattr(self.collection, name)

    def delete(self, **kwargs):
        self.deletes += 1
        if not self.noop:
            self.collection.delete(**kwargs)
        if self.fail_after:
            raise RuntimeError("fixture lost acknowledgement")


@unittest.skipUnless(os.getenv("MEMORIA_NATIVE_CHROMA_FIXTURES") == "1",
                     "explicit native Chroma fixture run required")
class NativeVectorCleanupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)/"new-fixture"
        self.db, self.client, self.collection, self.fid = create_cleanup_fixture(self.root)
        self.addCleanup(self.db.close)
        self.target = self.add("invented target")
        self.neighbor = self.add("invented neighbor")

    def add(self, text):
        mid = store_memory(self.db, {"app_name":"fixture", "content":text})
        self.seed(mid, text)
        return mid

    def seed(self, mid, text="invented stale vector", fixture_id=None):
        self.collection.upsert(ids=[str(mid)], documents=[text],
                               embeddings=[[1.0,0.0,0.0]],
                               metadatas=[{"fixture_id":fixture_id or self.fid,
                                           "native_id":str(mid)}])

    def ids(self, collection=None):
        collection = self.collection if collection is None else collection
        return set(collection.get(include=[])["ids"])

    def observation(self):
        row = self.db.execute("SELECT state FROM fixture_vector_observations WHERE memory_id=?",
                              (self.target,)).fetchone()
        return row[0] if row else None

    def clean(self, collection=None, fixture_id=None):
        return cleanup_fixture_vector(self.db,
                    self.collection if collection is None else collection,
                    self.fid if fixture_id is None else fixture_id, self.target)

    def test_native_delete_verify_and_repeat(self):
        delete_memory(self.db,self.target)
        receipt = self.clean()
        self.assertEqual(receipt["vector_observation"],ABSENT)
        self.assertEqual(receipt["vector_state"],PENDING)
        self.assertEqual(receipt["external_state"],"UNKNOWN")
        self.assertEqual(receipt["authority"],"NONE")
        self.assertEqual(self.ids(),{str(self.neighbor)})
        wrapper = FaultCollection(self.collection,noop=True)
        self.assertEqual(self.clean(wrapper),receipt)
        self.assertEqual(wrapper.deletes,0)
        self.assertEqual(self.observation(),ABSENT)
        self.assertEqual(tuple(self.db.execute(
            "SELECT vector_state,external_state FROM memory_forget_intents").fetchone()),
            (PENDING,"UNKNOWN"))

    def test_live_primary_and_missing_intent_refused(self):
        with self.assertRaisesRegex(PermissionError,"primary memory"):
            self.clean()
        self.assertEqual(self.ids(),{str(self.target),str(self.neighbor)})
        self.assertIsNone(self.observation())
        with self.assertRaisesRegex(PermissionError,"deletion intent"):
            cleanup_fixture_vector(self.db,self.collection,self.fid,999)

    def test_unrelated_collection_and_wrong_fixture_refused(self):
        other = self.client.create_collection(name="unrelated-fixture",embedding_function=None,
                    metadata={"schema":SCHEMA,"fixture_id":self.fid})
        other.upsert(ids=[str(self.target)],embeddings=[[0.0,1.0,0.0]])
        delete_memory(self.db,self.target)
        with self.assertRaisesRegex(PermissionError,"collection mismatch"):
            self.clean(other)
        with self.assertRaises(PermissionError):
            self.clean(fixture_id="fixture:"+"0"*32)
        self.assertEqual(self.ids(other),{str(self.target)})
        self.assertIn(str(self.target),self.ids())
        self.assertIsNone(self.observation())

    def test_vector_record_binding_mismatch_refused(self):
        delete_memory(self.db,self.target)
        self.seed(self.target,fixture_id="fixture:"+"0"*32)
        with self.assertRaisesRegex(PermissionError,"record binding mismatch"):
            self.clean()
        self.assertIn(str(self.target),self.ids())
        self.assertEqual(self.observation(),PENDING)

    def test_delete_noop_keeps_pending_after_prior_observation(self):
        delete_memory(self.db,self.target)
        self.clean()
        self.seed(self.target)
        with self.assertRaisesRegex(RuntimeError,"absence not observed"):
            self.clean(FaultCollection(self.collection,noop=True))
        self.assertEqual(self.observation(),PENDING)
        self.assertIn(str(self.target),self.ids())
        self.assertEqual(self.clean()["vector_observation"],ABSENT)
        self.assertEqual(self.ids(),{str(self.neighbor)})

    def test_lost_acknowledgement_retries_without_second_delete(self):
        delete_memory(self.db,self.target)
        with self.assertRaisesRegex(RuntimeError,"lost acknowledgement"):
            self.clean(FaultCollection(self.collection,fail_after=True))
        self.assertEqual(self.observation(),PENDING)
        self.assertNotIn(str(self.target),self.ids())
        wrapper = FaultCollection(self.collection,noop=True)
        self.assertEqual(self.clean(wrapper)["vector_observation"],ABSENT)
        self.assertEqual(wrapper.deletes,0)

    def test_existing_path_refused_and_caller_transaction_untouched(self):
        with self.assertRaises(FileExistsError):
            create_cleanup_fixture(self.root)
        delete_memory(self.db,self.target)
        self.db.execute("BEGIN IMMEDIATE")
        try:
            with self.assertRaisesRegex(ValueError,"independent cleanup"):
                self.clean()
            self.assertTrue(self.db.in_transaction)
        finally:
            self.db.rollback()
        self.assertIsNone(self.observation())
        self.assertIn(str(self.target),self.ids())

    def test_observation_persists_in_reopened_sqlite(self):
        delete_memory(self.db,self.target)
        receipt = self.clean()
        with sqlite3.connect(self.root/"source.db") as reopened:
            row = reopened.execute("SELECT collection_id,state FROM fixture_vector_observations "
                                   "WHERE memory_id=?",(self.target,)).fetchone()
            self.assertEqual(row,(receipt["collection_id"],ABSENT))
        self.assertEqual(self.ids(),{str(self.neighbor)})


if __name__ == "__main__":
    unittest.main()
