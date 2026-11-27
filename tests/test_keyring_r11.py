"""Disposable keyring and scoped API tests; no real keys or vector service."""
import base64
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from backend.api import app
from db import storage
from db.keyring import KeyConfigurationError, Keyring, REDACTED, configured_cipher

KEY1 = base64.urlsafe_b64encode(b"1"*32).decode("ascii")
KEY2 = base64.urlsafe_b64encode(b"2"*32).decode("ascii")
TOKEN = "A"*43
PAYLOAD = "invented confidential text"
RULES = {"alpha": hashlib.sha256(TOKEN.encode()).hexdigest()}


class KeyringTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)/"fixture.db"
        db = patch.object(storage, "DB_PATH", self.path)
        db.start()
        self.addCleanup(db.stop)
        env = patch.dict(os.environ, {
            "MEMORIA_ENCRYPT_AT_REST": "1",
            "MEMORIA_ENCRYPTION_KEYS": json.dumps({"k1": KEY1}),
            "MEMORIA_ACTIVE_KEY_ID": "k1",
            "MEMORIA_API_TOKEN_SHA256": json.dumps(RULES),
            "MEMORIA_KEY": "fixture legacy password",
        })
        env.start()
        self.addCleanup(env.stop)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        with closing(storage.get_connection()) as conn:
            storage.set_permission(conn, "alpha", True, True)

    def add(self, content=PAYLOAD, app_name="alpha", cipher=None):
        with closing(storage.get_connection()) as conn:
            return storage.store_memory(conn, {"content":content,"app_name":app_name},
                                        cipher=cipher)

    def rows(self, cipher=None, app_name=None):
        with closing(storage.get_connection()) as conn:
            return storage.query_memories(conn, app_name=app_name, cipher=cipher)

    def raw(self):
        with closing(storage.get_connection()) as conn:
            return [tuple(row) for row in conn.execute(
                "SELECT id,content,encrypted FROM memories ORDER BY id")]

    def post(self, **payload):
        return self.client.post("/memoria/store", headers={"Authorization":"Bearer "+TOKEN},
                                json={"app_name":"alpha","content":PAYLOAD,**payload})

    def query(self, **params):
        return self.client.get("/memoria/query", headers={"Authorization":"Bearer "+TOKEN},
                               params=params)

    def test_no_fallback_even_with_legacy_password(self):
        with patch.dict(os.environ, {"MEMORIA_ENCRYPTION_KEYS":""}):
            with self.assertRaises(KeyConfigurationError):
                storage.get_cipher(True)
            self.assertEqual(self.post().status_code, 503)
            self.assertEqual(self.query().status_code, 503)
        self.assertEqual(self.raw(), [])

    def test_reject_malformed_duplicate_and_missing_active_keys(self):
        cases = [("", "k1"), ("[]", "k1"), (json.dumps({"k1":"password"}), "k1"),
                 (json.dumps({"k1":KEY1}), "missing"),
                 (json.dumps({"k1":KEY1,"k2":KEY1}), "k1"),
                 ('{"k1":"'+KEY1+'","k1":"'+KEY2+'"}', "k1"),
                 (json.dumps({"bad:id":KEY1}), "bad:id")]
        for raw, active in cases:
            with self.subTest(active=active), patch.dict(os.environ, {
                "MEMORIA_ENCRYPTION_KEYS":raw,"MEMORIA_ACTIVE_KEY_ID":active}):
                with self.assertRaises(KeyConfigurationError):
                    configured_cipher()

    def test_explicit_mode_only(self):
        with patch.dict(os.environ, {"MEMORIA_ENCRYPT_AT_REST":"0"}):
            self.assertIsNone(configured_cipher())
        with patch.dict(os.environ, {"MEMORIA_ENCRYPT_AT_REST":"yes"}):
            self.assertEqual(self.post().status_code, 503)
            self.assertEqual(self.query().status_code, 503)
        self.assertEqual(self.raw(), [])

    def test_roundtrip_randomized_text_envelope_and_no_plaintext(self):
        keyring = configured_cipher()
        self.add(cipher=keyring)
        self.add(cipher=keyring)
        raw = self.raw()
        self.assertTrue(all(row[1].startswith("memoria:v1:k1:") and row[2]==1 for row in raw))
        self.assertNotEqual(raw[0][1], raw[1][1])
        self.assertNotIn(PAYLOAD, repr(raw))
        self.assertEqual([row["content"] for row in self.rows(keyring)], [PAYLOAD, PAYLOAD])
        self.assertEqual([row["content"] for row in self.rows()], [REDACTED, REDACTED])

    def test_rotation_changes_new_writes_without_rewriting_old(self):
        self.add("first", cipher=configured_cipher())
        before = self.raw()[0]
        with patch.dict(os.environ, {"MEMORIA_ENCRYPTION_KEYS":json.dumps({"k1":KEY1,"k2":KEY2}),
                                     "MEMORIA_ACTIVE_KEY_ID":"k2"}):
            self.add("second", cipher=configured_cipher())
            self.assertEqual(self.raw()[0], before)
            self.assertTrue(self.raw()[1][1].startswith("memoria:v1:k2:"))
            self.assertEqual({r["content"] for r in self.rows(configured_cipher())}, {"first","second"})
        only_new = Keyring({"k2":KEY2}, "k2")
        self.assertEqual({r["content"] for r in self.rows(only_new)}, {REDACTED,"second"})
        self.assertEqual(self.raw()[0], before)

    def test_wrong_key_and_tampering_redact(self):
        ring = configured_cipher()
        value = ring.seal(PAYLOAD, "alpha")
        self.assertEqual(Keyring({"k1":KEY2},"k1").open(value,"alpha"), REDACTED)
        prefix, token = value.rsplit(":",1)
        changed = ("A" if token[0]!="A" else "B")+token[1:]
        self.assertEqual(ring.open(prefix+":"+changed,"alpha"), REDACTED)
        self.assertEqual(ring.open(value.replace(":k1:",":other:"),"alpha"), REDACTED)

    def test_cross_application_ciphertext_substitution_redacts(self):
        ring = configured_cipher()
        self.add(cipher=ring)
        with closing(storage.get_connection()) as conn:
            conn.execute("UPDATE memories SET app_name='beta'")
            conn.commit()
        self.assertEqual(self.rows(ring, "beta")[0]["content"], REDACTED)

    def test_legacy_ciphertext_is_not_migrated_or_decrypted(self):
        legacy = Fernet(KEY1.encode()).encrypt(PAYLOAD.encode()).decode()
        self.add("fixture placeholder")
        with closing(storage.get_connection()) as conn:
            conn.execute("UPDATE memories SET content=?,encrypted=1", (legacy,))
            conn.commit()
        before = self.raw()
        self.assertEqual(self.rows(configured_cipher())[0]["content"], REDACTED)
        self.assertEqual(self.raw(), before)

    def test_http_encrypted_write_and_scoped_read(self):
        result = self.post()
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["index_status"], "HELD")
        self.assertNotIn(PAYLOAD, repr(self.raw()))
        self.assertEqual(self.query().json()["items"][0]["content"], PAYLOAD)
        self.assertEqual(self.query(app_name="beta").status_code, 403)
        with patch.dict(os.environ, {"MEMORIA_ENCRYPT_AT_REST":"0"}):
            self.assertEqual(self.query().json()["items"][0]["content"], REDACTED)

    def test_permission_revocation_still_blocks_decryption(self):
        self.assertEqual(self.post().status_code, 200)
        with closing(storage.get_connection()) as conn:
            storage.set_permission(conn, "alpha", False, False)
        self.assertEqual(self.query().status_code, 403)
        self.assertEqual(self.post().status_code, 403)


if __name__ == "__main__":
    unittest.main()
