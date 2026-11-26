import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from db.genomememory_export import create_fixture, export_fixture_metadata
from db.storage import store_memory, set_permission


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'source.sqlite3'
        self.conn = create_fixture(self.path, 'fixture:memoria')
        for app in ('demo', 'other'):
            store_memory(self.conn, dict(content='SYNTHETIC PAYLOAD '+app, app_name=app,
                agent_id='fixture:author', timestamp='2026-06-20T12:00:00+00:00',
                tags=['research'], importance_score=1, metadata={'private': 'NO EXPORT'}))

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()

    def export(self, **kwargs):
        return export_fixture_metadata(self.conn, expected_app='demo',
                                       fixture_id=kwargs.get('fixture_id', 'fixture:memoria'))

    def test_missing_and_revoked_permission_deny(self):
        with self.assertRaises(PermissionError): self.export()
        set_permission(self.conn, 'demo', True, False)
        self.assertEqual(len(self.export()['rows']), 1)
        set_permission(self.conn, 'demo', False, True)
        with self.assertRaises(PermissionError): self.export()

    def test_payload_excluded_and_scope_exact(self):
        set_permission(self.conn, 'demo', True, False)
        statements = []
        self.conn.set_trace_callback(statements.append)
        result = self.export()
        self.assertNotIn('SYNTHETIC PAYLOAD', json.dumps(result))
        self.assertNotIn('NO EXPORT', json.dumps(result))
        self.assertEqual([r['app_name'] for r in result['rows']], ['demo'])
        self.assertTrue(all('content' not in s and 'metadata_json' not in s for s in statements))
        self.assertTrue(all(s.startswith('SELECT') for s in statements))

    def test_existing_path_and_wrong_fixture_refused(self):
        with self.assertRaises(FileExistsError): create_fixture(self.path, 'fixture:x')
        with self.assertRaises(PermissionError): self.export(fixture_id='fixture:wrong')

    def test_unmarked_source_is_not_modified(self):
        db = sqlite3.connect(':memory:')
        before = db.total_changes
        with self.assertRaises(sqlite3.OperationalError):
            export_fixture_metadata(db, expected_app='demo', fixture_id='fixture:memoria')
        self.assertEqual(db.total_changes, before)
        db.close()

