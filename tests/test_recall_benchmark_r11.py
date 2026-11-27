"""Cross-check the actual native recall API ranking against the ASCII fixture."""
import json
from pathlib import Path
import sqlite3
import unittest

from db.private_recall import recall_with_cipher
from db.storage import init_db, set_permission, store_memory

ROOT = Path(__file__).resolve().parents[1] / "research" / "recall"


class RecallBenchmarkR11(unittest.TestCase):
    def test_native_jaccard_matches_all_frozen_fixture_queries(self):
        fixture = json.loads((ROOT / "fixture-v1.json").read_text(encoding="utf-8"))
        report = json.loads((ROOT / "results-v1.json").read_text(encoding="utf-8"))
        reference = {row["query_id"]: row for row in report["rows"]
                     if row["method"] == "jaccard"}
        conn = sqlite3.connect(":memory:")
        self.addCleanup(conn.close)
        init_db(conn)
        set_permission(conn, "fixture", True, False)
        for doc in fixture["documents"]:
            mid = store_memory(conn, {"app_name": "fixture", "content": doc["text"]})
            self.assertEqual(mid, doc["id"])
        store_memory(conn, {"app_name": "unrelated", "content": "router warranty refund"})
        self.assertEqual(len(reference), 24)
        for query in fixture["queries"]:
            with self.subTest(query=query["id"]):
                conn.execute("BEGIN IMMEDIATE")
                try:
                    actual = recall_with_cipher(conn, "fixture", query["text"], limit=3)
                finally:
                    conn.rollback()
                expected = reference[query["id"]]["top"]
                self.assertEqual([item["id"] for item in actual["items"]],
                                 [item["id"] for item in expected])
                for item, baseline in zip(actual["items"], expected):
                    score = item["score"]
                    self.assertAlmostEqual(score["numerator"] / score["denominator"],
                                           baseline["score"], places=11)
                self.assertEqual(actual["authority"], "NONE")


if __name__ == "__main__":
    unittest.main()
