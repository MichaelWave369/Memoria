"""Explicitly scoped metadata export from disposable native Memoria fixtures.

No API import, default DB access, cipher, vector collection or network use.
The fixture marker is a guardrail, not authentication or a sandbox.
"""
import json
import os
import re
import sqlite3
from pathlib import Path

SOURCE_REVISION = '9c480fcaea467615252d347956eac42ff038edf7'
SCHEMA = 'genomememory-memoria-fixture/r0.4'


def _label(value):
    if type(value) is not str or not re.fullmatch(r'[A-Za-z0-9._:-]{1,128}', value):
        raise ValueError('invalid scope or fixture label')
    return value


def create_fixture(path, fixture_id):
    """Create only a new file using the existing native schema initializer."""
    fixture_id = _label(fixture_id)
    if not fixture_id.startswith('fixture:') or fixture_id == 'fixture:':
        raise ValueError('explicit fixture ID required')
    path = Path(path)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        from db.storage import init_db
        init_db(conn)
        conn.execute('CREATE TABLE genomememory_fixture (fixture_id TEXT PRIMARY KEY)')
        conn.execute('INSERT INTO genomememory_fixture VALUES (?)', (fixture_id,))
        conn.commit()
        return conn
    except BaseException:
        conn.close()
        raise


def export_fixture_metadata(conn, *, expected_app, fixture_id):
    """Read seven metadata columns after native explicit can_read=1.

    Local caller controls the SQLite connection and is inside the trust boundary.
    This is not an authenticated public API and must not be wired to one.
    Missing app policy denies; no app-wide or unscoped export is supported.
    """
    expected_app, fixture_id = _label(expected_app), _label(fixture_id)
    # This function does not install markers or mutate any source schema.
    markers = conn.execute('SELECT fixture_id FROM genomememory_fixture').fetchall()
    if len(markers) != 1 or markers[0][0] != fixture_id:
        raise PermissionError('disposable fixture identity mismatch')
    permission = conn.execute('SELECT can_read FROM app_permissions WHERE app_name=?',
                              (expected_app,)).fetchone()
    if permission is None or permission[0] != 1:
        raise PermissionError('explicit native read permission required')
    rows = conn.execute('''SELECT id,app_name,agent_id,timestamp,tags,importance_score,encrypted
                           FROM memories WHERE app_name=? ORDER BY id LIMIT 257''',
                        (expected_app,)).fetchall()
    if not 1 <= len(rows) <= 256:
        raise ValueError('fixture row count outside 1..256')
    columns = ('id', 'app_name', 'agent_id', 'timestamp', 'tags', 'importance_score', 'encrypted')
    out = [dict(zip(columns, row)) for row in rows]
    for row in out:
        row['tags'] = json.loads(row['tags'])
    return dict(schema=SCHEMA, synthetic=True, source_revision=SOURCE_REVISION,
                fixture_id=fixture_id, rows=out)

