"""Native Chroma cleanup for newly created disposable fixture pairs only.

The current intent ledger remains PENDING_UNVERIFIED/UNKNOWN. A separate
observation records logical absence from one explicitly bound collection.
No default paths, embedding service, API route or production authority.
"""
from pathlib import Path
import re
import uuid

from db.genomememory_export import create_fixture

SCHEMA = "memoria-vector-cleanup-fixture/v1"
ABSENT = "ABSENT_OBSERVED"
PENDING = "PENDING_UNVERIFIED"


def create_cleanup_fixture(root):
    """Create a new directory and native SQLite/Chroma pair; never adopt one."""
    import chromadb
    from chromadb.config import Settings

    root = Path(root)
    root.mkdir(mode=0o700, exist_ok=False)
    suffix = uuid.uuid4().hex
    fixture_id = "fixture:" + suffix
    name = "memoria-fixture-" + suffix
    conn = create_fixture(root / "source.db", fixture_id)
    try:
        client = chromadb.PersistentClient(path=str(root / "chroma"),
                                          settings=Settings(anonymized_telemetry=False))
        collection = client.create_collection(name=name, embedding_function=None,
                                              metadata={"schema": SCHEMA, "fixture_id": fixture_id})
        conn.execute("""CREATE TABLE fixture_vector_binding (
                        fixture_id TEXT PRIMARY KEY, collection_name TEXT NOT NULL,
                        collection_id TEXT NOT NULL)""")
        conn.execute("INSERT INTO fixture_vector_binding VALUES (?,?,?)",
                     (fixture_id, name, str(collection.id)))
        conn.execute("""CREATE TABLE fixture_vector_observations (
                        memory_id INTEGER PRIMARY KEY,
                        collection_id TEXT NOT NULL,
                        state TEXT NOT NULL CHECK(state IN ('PENDING_UNVERIFIED','ABSENT_OBSERVED'))
                        )""")
        conn.commit()
        return conn, client, collection, fixture_id
    except BaseException:
        conn.close()
        raise


def _binding(conn, collection, fixture_id):
    if type(fixture_id) is not str or not re.fullmatch(r"fixture:[a-f0-9]{32}", fixture_id):
        raise PermissionError("explicit cleanup fixture required")
    markers = conn.execute("SELECT fixture_id FROM genomememory_fixture").fetchall()
    rows = conn.execute("SELECT fixture_id,collection_name,collection_id FROM fixture_vector_binding").fetchall()
    expected_name = "memoria-fixture-" + fixture_id.split(":", 1)[1]
    if (len(markers) != 1 or markers[0][0] != fixture_id or len(rows) != 1
            or tuple(rows[0]) != (fixture_id, expected_name, str(collection.id))
            or collection.name != expected_name
            or collection.metadata != {"schema": SCHEMA, "fixture_id": fixture_id}):
        raise PermissionError("cleanup fixture collection mismatch")
    return str(collection.id)


def _eligible(conn, memory_id):
    if conn.execute("SELECT 1 FROM memories WHERE id=?", (memory_id,)).fetchone():
        raise PermissionError("primary memory still exists")
    row = conn.execute(
        "SELECT vector_state,external_state FROM memory_forget_intents WHERE memory_id=?",
        (memory_id,)).fetchone()
    if row is None or tuple(row) != (PENDING, "UNKNOWN"):
        raise PermissionError("durable deletion intent required")


def _observe(conn, memory_id, collection_id, state):
    conn.execute("""INSERT INTO fixture_vector_observations VALUES (?,?,?)
                    ON CONFLICT(memory_id) DO UPDATE SET
                    collection_id=excluded.collection_id,state=excluded.state""",
                 (memory_id, collection_id, state))


def cleanup_fixture_vector(conn, collection, fixture_id, memory_id):
    """Inspect/delete one bound native vector ID, then check logical absence.

    Exclusive trusted fixture owner only. No concurrent Chroma writers,
    attacker-controlled handles, restored real databases or live service.
    """
    if type(memory_id) is not int or not 1 <= memory_id <= 2**63-1:
        raise ValueError("invalid memory ID")
    if conn.in_transaction:
        raise ValueError("independent cleanup transaction required")
    # Commit pending before calling Chroma. A crash or failure in the
    # second transaction cannot leave a previous success as current.
    with conn:
        conn.execute("BEGIN IMMEDIATE")
        collection_id = _binding(conn, collection, fixture_id)
        _eligible(conn, memory_id)
        _observe(conn, memory_id, collection_id, PENDING)
    native_id = str(memory_id)
    with conn:
        conn.execute("BEGIN IMMEDIATE")
        if _binding(conn, collection, fixture_id) != collection_id:
            raise PermissionError("cleanup collection changed")
        _eligible(conn, memory_id)
        before = collection.get(ids=[native_id], include=["metadatas"])
        ids = before.get("ids")
        if ids == [native_id]:
            if before.get("metadatas") != [{"fixture_id": fixture_id, "native_id": native_id}]:
                raise PermissionError("vector record binding mismatch")
            collection.delete(ids=[native_id])
        elif ids != []:
            raise RuntimeError("unexpected native vector lookup result")
        after = collection.get(ids=[native_id], include=[])
        if after.get("ids") != []:
            raise RuntimeError("vector absence not observed")
        _observe(conn, memory_id, collection_id, ABSENT)
    return {"memory_id": memory_id, "collection_id": collection_id,
            "vector_observation": ABSENT, "vector_state": PENDING,
            "external_state": "UNKNOWN", "authority": "NONE"}
