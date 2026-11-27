"""Durable logical deletion intent, disposable stores only."""
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

from db.storage import init_db, store_memory, delete_memory, query_memories, set_permission
from db.private_recall import recall_with_cipher


class ForgetIntentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "fixture.db"
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.addCleanup(self.db.close)
        init_db(self.db)
        set_permission(self.db, "fixture", True, True)
        self.first = self.add("invented private payload")
        self.other = self.add("unrelated payload")

    def add(self, text):
        return store_memory(self.db, {"app_name": "fixture", "content": text,
                                     "tags": ["invented-tag"], "metadata": {"source": "invented-source"}})

    def intents(self, conn=None):
        conn = self.db if conn is None else conn
        return [tuple(row) for row in conn.execute(
            "SELECT memory_id,vector_state,external_state FROM memory_forget_intents ORDER BY memory_id")]

    def expected(self):
        return {"memory_id": self.first, "status": "LOGICALLY_DELETED",
                "vector_state": "PENDING_UNVERIFIED", "external_state": "UNKNOWN",
                "authority": "NONE"}

    def test_atomic_intent_and_unrelated_record_preservation(self):
        self.assertEqual(delete_memory(self.db, self.first), self.expected())
        self.assertEqual(self.intents(), [(self.first, "PENDING_UNVERIFIED", "UNKNOWN")])
        self.assertEqual([r["id"] for r in query_memories(self.db)], [self.other])
        self.assertNotIn("invented private payload", "\n".join(self.db.iterdump()))

    def test_repeat_and_reopen_preserve_single_intent(self):
        first = delete_memory(self.db, self.first)
        before = self.db.total_changes
        self.assertEqual(delete_memory(self.db, self.first), first)
        self.assertEqual(self.db.total_changes, before)
        with closing(sqlite3.connect(self.path)) as reopened:
            init_db(reopened)
            self.assertEqual(delete_memory(reopened, self.first), first)
            self.assertEqual(self.intents(reopened), self.intents())
            self.assertEqual(reopened.execute("PRAGMA integrity_check").fetchone()[0], "ok")

    def test_nonexistent_id_does_not_create_tombstone(self):
        self.assertEqual(delete_memory(self.db, 999), {"memory_id":999,
                         "status":"NOT_FOUND", "authority":"NONE"})
        self.assertEqual(self.intents(), [])

    def test_direct_sql_delete_rolls_back_intent_with_record(self):
        self.db.execute("BEGIN IMMEDIATE")
        self.db.execute("DELETE FROM memories WHERE id=?", (self.first,))
        self.assertEqual(len(self.intents()), 1)
        self.db.rollback()
        self.assertEqual(self.intents(), [])
        self.assertEqual(self.db.execute("SELECT count(*) FROM memories").fetchone()[0], 2)

    def test_committed_direct_sql_delete_records_intent(self):
        self.db.execute("DELETE FROM memories WHERE id=?", (self.first,))
        self.db.commit()
        self.assertEqual(delete_memory(self.db, self.first), self.expected())
        self.assertEqual(len(self.intents()), 1)

    def test_missing_intent_trigger_rolls_back_native_deletion(self):
        self.db.execute("DROP TRIGGER memoria_record_forget")
        self.db.commit()
        with self.assertRaisesRegex(RuntimeError, "intent missing"):
            delete_memory(self.db, self.first)
        self.assertEqual(self.db.execute("SELECT count(*) FROM memories").fetchone()[0], 2)
        self.assertEqual(self.intents(), [])

    def test_trigger_failure_preserves_primary_record(self):
        self.db.execute("""CREATE TRIGGER fixture_fail_intent BEFORE INSERT
                        ON memory_forget_intents BEGIN
                        SELECT RAISE(ABORT,'fixture interruption'); END""")
        self.db.commit()
        with self.assertRaises(sqlite3.IntegrityError):
            delete_memory(self.db, self.first)
        self.assertEqual(self.db.execute("SELECT count(*) FROM memories").fetchone()[0], 2)
        self.assertEqual(self.intents(), [])

    def test_explicit_id_resurrection_refused(self):
        delete_memory(self.db, self.first)
        with self.assertRaisesRegex(sqlite3.IntegrityError, "forgotten memory ID"):
            with self.db:
                self.db.execute("""INSERT INTO memories
                    (id,content,app_name,agent_id,timestamp,tags,importance_score,metadata_json)
                    VALUES (?, 'restored','fixture','a','now','[]',0.5,'{}')""", (self.first,))
        with self.assertRaisesRegex(sqlite3.IntegrityError, "forgotten memory ID"):
            with self.db:
                self.db.execute("UPDATE memories SET id=? WHERE id=?", (self.first, self.other))
        self.assertGreater(self.add("new record"), self.other)
        self.assertEqual(len(self.intents()), 1)

    def test_deletion_does_not_commit_unrelated_transaction(self):
        self.db.execute("BEGIN IMMEDIATE")
        self.db.execute("UPDATE memories SET content='uncommitted' WHERE id=?", (self.other,))
        with self.assertRaisesRegex(ValueError, "independent transaction"):
            delete_memory(self.db, self.first)
        self.db.rollback()
        self.assertEqual(self.db.execute("SELECT content FROM memories WHERE id=?", (self.other,)).fetchone()[0],
                         "unrelated payload")
        self.assertEqual(self.intents(), [])

    def test_deleted_record_not_in_scoped_recall(self):
        def recall():
            self.db.execute("BEGIN IMMEDIATE")
            try:
                return recall_with_cipher(self.db, "fixture", "private")["items"]
            finally:
                self.db.rollback()
        self.assertEqual([item["id"] for item in recall()], [self.first])
        delete_memory(self.db, self.first)
        self.assertEqual(recall(), [])

    def test_intent_schema_has_no_payload_and_cannot_claim_verified(self):
        delete_memory(self.db, self.first)
        columns = [r[1] for r in self.db.execute("PRAGMA table_info(memory_forget_intents)")]
        self.assertEqual(columns, ["memory_id","vector_state","external_state"])
        for column in ("vector_state","external_state"):
            with self.assertRaises(sqlite3.IntegrityError):
                with self.db:
                    self.db.execute("UPDATE memory_forget_intents SET "+column+"='VERIFIED'")

    def test_invalid_ids_refused(self):
        for value in (True, 0, -1, "1", 2**63):
            with self.subTest(value=value), self.assertRaises(ValueError):
                delete_memory(self.db, value)
        self.assertEqual(self.intents(), [])


if __name__ == "__main__":
    unittest.main()
