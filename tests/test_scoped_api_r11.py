"""HTTP route regressions with disposable SQLite data, no vector service."""
from contextlib import closing
from datetime import datetime
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

ALPHA = "A"*43
BETA = "B"*43
RULES = {"alpha": hashlib.sha256(ALPHA.encode()).hexdigest(),
         "beta": hashlib.sha256(BETA.encode()).hexdigest()}


class ScopedApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)/"fixture.db"
        db_patch = patch.object(storage, "DB_PATH", self.path)
        db_patch.start()
        self.addCleanup(db_patch.stop)
        env = patch.dict(os.environ, {"MEMORIA_API_TOKEN_SHA256": json.dumps(RULES),
                                      "MEMORIA_ENCRYPT_AT_REST": "0"})
        env.start()
        self.addCleanup(env.stop)
        with closing(storage.get_connection()) as conn:
            for name in ("alpha", "beta", "unregistered"):
                storage.store_memory(conn, dict(content="invented "+name,
                    app_name=name, agent_id="fixture", tags=[name],
                    timestamp=datetime.utcnow().isoformat()))
            storage.set_permission(conn, "alpha", True, True)
            storage.set_permission(conn, "beta", True, True)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def headers(self, token=ALPHA):
        return {"Authorization": "Bearer "+token}

    def query(self, **params):
        return self.client.get("/memoria/query", params=params, headers=self.headers())

    def payload(self, name="alpha"):
        return {"app_name": name, "content": "new invented payload"}

    def permission(self, name, read, write):
        with closing(storage.get_connection()) as conn:
            storage.set_permission(conn, name, read, write)

    def test_missing_and_bad_credentials_do_not_read_database(self):
        with patch("backend.api.get_connection", side_effect=AssertionError("unexpected DB access")):
            self.assertEqual(self.client.get("/memoria/query").status_code, 401)
            response = self.client.get("/memoria/query", headers=self.headers("X"*43))
            self.assertEqual(response.status_code, 401)
            self.assertNotIn("invented", response.text)

    def test_absent_duplicate_or_malformed_registry_fails_closed(self):
        for raw in ("", "[]", '{"alpha":"bad"}',
                    '{"alpha":"'+RULES["alpha"]+'","alpha":"'+RULES["beta"]+'"}',
                    json.dumps({"alpha": RULES["alpha"], "beta": RULES["alpha"]})):
            with self.subTest(raw=raw), patch.dict(os.environ, {"MEMORIA_API_TOKEN_SHA256":raw}):
                response = self.query()
                self.assertEqual(response.status_code, 503)

    def test_query_defaults_to_authenticated_app_and_denies_cross_scope(self):
        response = self.query()
        self.assertEqual(response.status_code, 200)
        self.assertEqual([m["app_name"] for m in response.json()["items"]], ["alpha"])
        self.assertEqual(self.query(app_name="beta").status_code, 403)
        self.assertEqual(self.query(app_name="").status_code, 403)
        other = self.client.get("/memoria/query", headers=self.headers(BETA))
        self.assertEqual([m["app_name"] for m in other.json()["items"]], ["beta"])

    def test_revoked_and_missing_read_permission(self):
        self.permission("alpha", False, True)
        self.assertEqual(self.query().status_code, 403)
        with closing(storage.get_connection()) as conn:
            conn.execute("DELETE FROM app_permissions WHERE app_name='alpha'")
            conn.commit()
        self.assertEqual(self.query().status_code, 403)

    def test_store_scope_and_explicit_write_permission(self):
        self.assertEqual(self.client.post("/memoria/store", headers=self.headers(),
                         json=self.payload("beta")).status_code, 403)
        self.permission("alpha", True, False)
        self.assertEqual(self.client.post("/memoria/store", headers=self.headers(),
                         json=self.payload()).status_code, 403)
        self.permission("alpha", True, True)
        response = self.client.post("/memoria/store", headers=self.headers(), json=self.payload())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["index_status"], "HELD")
        self.assertEqual(self.query().json()["count"], 2)

    def test_registered_credential_without_native_policy_cannot_write(self):
        with closing(storage.get_connection()) as conn:
            conn.execute("DELETE FROM app_permissions WHERE app_name='alpha'")
            conn.commit()
        self.assertEqual(self.client.post("/memoria/store", headers=self.headers(),
                         json=self.payload()).status_code, 403)

    def test_synthesis_is_scoped_and_requires_current_read_permission(self):
        response = self.client.get("/memoria/synthesis", headers=self.headers())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["summary"]["top_apps"], [["alpha", 1]])
        self.assertEqual(response.json()["summary"]["top_tags"], [["alpha", 1]])
        self.permission("alpha", False, True)
        self.assertEqual(self.client.get("/memoria/synthesis", headers=self.headers()).status_code, 403)

    def test_unsafe_routes_held_and_cannot_mutate(self):
        for method, path, data in [
            ("POST", "/memoria/semantic", {"text":"invented"}),
            ("DELETE", "/memoria/1", None),
            ("GET", "/permissions", None),
            ("POST", "/permissions/beta?can_read=false&can_write=false", None),
        ]:
            with self.subTest(path=path):
                args = {"json": data} if data is not None else {}
                self.assertEqual(self.client.request(method, path, **args).status_code, 401)
                self.assertEqual(self.client.request(method, path, headers=self.headers(), **args).status_code, 503)
        self.assertEqual(self.query().json()["count"], 1)
        with closing(storage.get_connection()) as conn:
            self.assertEqual(conn.execute("SELECT can_read,can_write FROM app_permissions WHERE app_name='beta'").fetchone()[:], (1,1))

    def test_encryption_request_never_silently_stores_plaintext(self):
        with patch.dict(os.environ, {"MEMORIA_ENCRYPT_AT_REST":"1"}):
            self.assertEqual(self.client.post("/memoria/store", headers=self.headers(),
                             json=self.payload()).status_code, 503)
        self.assertEqual(self.query().json()["count"], 1)

    def test_encrypted_existing_text_not_decrypted_by_api(self):
        with closing(storage.get_connection()) as conn:
            conn.execute("UPDATE memories SET encrypted=1,content='fixture-ciphertext' WHERE app_name='alpha'")
            conn.commit()
        response = self.query()
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("fixture-ciphertext", response.text)
        self.assertIn("Encrypted memory", response.json()["items"][0]["content"])

    def test_query_bounds(self):
        self.assertEqual(self.query(limit=0).status_code, 422)
        self.assertEqual(self.query(limit=501).status_code, 422)
        self.assertEqual(self.client.get("/memoria/synthesis?window=other", headers=self.headers()).status_code, 422)


if __name__ == "__main__":
    unittest.main()
