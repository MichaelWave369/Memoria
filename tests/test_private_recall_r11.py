"""Scoped recall on disposable SQLite, no persistent vector or model service."""
import base64
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from backend.api import app
from db import storage
from db.keyring import Keyring
from db.private_recall import recall_with_cipher

TOKEN = "A"*43
OTHER = "B"*43
KEY = base64.urlsafe_b64encode(b"1"*32).decode("ascii")
RULES = {name:hashlib.sha256(token.encode()).hexdigest()
         for name,token in (("alpha",TOKEN),("beta",OTHER))}


class PrivateRecallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)/"fixture.db"
        db = patch.object(storage, "DB_PATH", self.path)
        db.start()
        self.addCleanup(db.stop)
        env = patch.dict(os.environ, {"MEMORIA_API_TOKEN_SHA256":json.dumps(RULES),
                                      "MEMORIA_ENCRYPT_AT_REST":"0",
                                      "MEMORIA_ENCRYPTION_KEYS":json.dumps({"key":KEY}),
                                      "MEMORIA_ACTIVE_KEY_ID":"key"})
        env.start()
        self.addCleanup(env.stop)
        with closing(storage.get_connection()) as conn:
            storage.set_permission(conn,"alpha",True,True)
            storage.set_permission(conn,"beta",True,True)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def add(self, content, name="alpha", cipher=None):
        with closing(storage.get_connection()) as conn:
            return storage.store_memory(conn, {"content":content,"app_name":name}, cipher)

    def search(self, text, limit=5, token=TOKEN):
        headers = {} if token is None else {"Authorization":"Bearer "+token}
        return self.client.post("/memoria/recall",headers=headers,
                                json={"text":text,"limit":limit})

    def items(self, text, **kwargs):
        result = self.search(text, **kwargs)
        self.assertEqual(result.status_code,200,result.text)
        self.assertEqual(result.json()["method"],"ephemeral-lexical-jaccard/v1")
        self.assertEqual(result.json()["authority"],"NONE")
        return result.json()["items"]

    def dump(self):
        with closing(storage.get_connection()) as conn:
            return tuple(conn.iterdump())

    def test_exact_ranking_and_ties(self):
        first = self.add("Apple banana")
        second = self.add("banana apple")
        partial = self.add("apple pear")
        self.add("orange")
        self.assertEqual(self.items("APPLE banana"),[
            {"id":first,"score":{"numerator":1,"denominator":1}},
            {"id":second,"score":{"numerator":1,"denominator":1}},
            {"id":partial,"score":{"numerator":1,"denominator":3}}])
        self.assertEqual([x["id"] for x in self.items("apple banana",limit=1)],[first])

    def test_scope_and_no_payload_or_metadata(self):
        own = self.add("invented secret")
        other = self.add("invented secret","beta")
        self.assertEqual([x["id"] for x in self.items("invented")],[own])
        self.assertEqual([x["id"] for x in self.items("invented",token=OTHER)],[other])
        result = self.search("invented")
        self.assertNotIn("invented", result.text)
        self.assertNotIn("secret", result.text)
        self.assertEqual(set(result.json()["items"][0]),{"id","score"})

    def test_authentication_before_database_access(self):
        with patch("backend.api.get_connection",side_effect=AssertionError("unexpected database access")):
            self.assertEqual(self.search("test",token=None).status_code,401)
            self.assertEqual(self.search("test",token="X"*43).status_code,401)

    def test_revocation_and_direct_call_without_transaction(self):
        self.add("test")
        with closing(storage.get_connection()) as conn:
            with self.assertRaises(PermissionError):
                recall_with_cipher(conn,"alpha","test")
            storage.set_permission(conn,"alpha",False,True)
        self.assertEqual(self.search("test").status_code,403)

    def test_encrypted_recall_requires_readable_bound_envelope(self):
        ring = Keyring({"key":KEY},"key")
        own = self.add("confidential apples",cipher=ring)
        self.add("confidential apples","beta",cipher=ring)
        bad = self.add("legacy")
        with closing(storage.get_connection()) as conn:
            conn.execute("UPDATE memories SET encrypted=1,content='legacy token' WHERE id=?",(bad,))
            conn.commit()
        self.assertEqual(self.items("confidential"),[])
        with patch.dict(os.environ,{"MEMORIA_ENCRYPT_AT_REST":"1"}):
            self.assertEqual([r["id"] for r in self.items("confidential")],[own])
            self.assertEqual(self.items("encrypted memory"),[])
        with patch.dict(os.environ,{"MEMORIA_ENCRYPT_AT_REST":"1","MEMORIA_ENCRYPTION_KEYS":""}):
            self.assertEqual(self.search("confidential").status_code,503)

    def test_no_match_and_unicode_casefold(self):
        mid = self.add("Straße")
        self.assertEqual([r["id"] for r in self.items("STRASSE")],[mid])
        self.assertEqual(self.items("unrelated"),[])

    def test_budget_rejects_excessive_scope_not_other_apps(self):
        self.add("match")
        self.add("x"*65537,"beta")
        self.assertEqual(len(self.items("match")),1)
        self.assertEqual(self.search("match",token=OTHER).status_code,503)
        self.add("x"*65537)
        self.assertEqual(self.search("match").status_code,503)

    def test_row_budget_abstains_without_partial_results(self):
        with closing(storage.get_connection()) as conn:
            for _ in range(257):
                storage.store_memory(conn,{"app_name":"alpha","content":"match"})
        response = self.search("match")
        self.assertEqual(response.status_code,503)
        self.assertNotIn("items",response.json())

    def test_total_byte_budget(self):
        with closing(storage.get_connection()) as conn:
            for _ in range(33):
                storage.store_memory(conn,{"app_name":"alpha","content":"x"*65536})
        self.assertEqual(self.search("x").status_code,503)

    def test_query_and_result_bounds(self):
        for text in ("", "!!!", "x"*513, " ".join("t"+str(i) for i in range(65))):
            self.assertEqual(self.search(text).status_code,422)
        for limit in (0,21,True,"5"):
            self.assertEqual(self.search("test",limit).status_code,422)

        response = self.client.post("/memoria/recall",headers={"Authorization":"Bearer "+TOKEN},
                                    json={"text":"test","app_name":"beta"})
        self.assertEqual(response.status_code,422)

    def test_read_only_and_deleted_row_disappears_without_index(self):
        mid = self.add("match")
        before = self.dump()
        self.assertEqual(len(self.items("match")),1)
        self.assertEqual(self.dump(),before)
        with closing(storage.get_connection()) as conn:
            storage.delete_memory(conn,mid)
        self.assertEqual(self.items("match"),[])
        self.assertEqual({p.name for p in Path(self.tmp.name).iterdir()}, {"fixture.db"})

    def test_legacy_semantic_route_remains_held(self):
        response = self.client.post("/memoria/semantic",headers={"Authorization":"Bearer "+TOKEN},
                                    json={"text":"test"})
        self.assertEqual(response.status_code,503)


if __name__ == "__main__":
    unittest.main()
