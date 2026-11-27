"""Cold reopen and bounded reconciliation of an explicitly bound synthetic pair."""
from pathlib import Path
import re
import sqlite3

from db.fixture_vector_cleanup import _binding, cleanup_fixture_vector, ABSENT

MAX_RECORDS = 256


def reopen_fixture(root, fixture_id, collection_id):
    """Reopen only a previously bound fixture; never create or adopt a collection."""
    import chromadb
    from chromadb.config import Settings

    if type(fixture_id) is not str or not re.fullmatch(r"fixture:[a-f0-9]{32}", fixture_id):
        raise PermissionError("explicit fixture identity required")
    if type(collection_id) is not str or not re.fullmatch(
            r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}", collection_id):
        raise PermissionError("explicit collection identity required")
    root = Path(root)
    source, chroma = root / "source.db", root / "chroma"
    if (any(p.is_symlink() for p in (root, source, chroma, chroma/"chroma.sqlite3"))
            or not root.is_dir() or not source.is_file()
            or not chroma.is_dir() or not (chroma/"chroma.sqlite3").is_file()):
        raise PermissionError("existing fixture pair required")
    conn = sqlite3.connect(source.resolve().as_uri()+"?mode=rw", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        name = "memoria-fixture-" + fixture_id.split(":",1)[1]
        markers = conn.execute("SELECT fixture_id FROM genomememory_fixture").fetchall()
        rows = conn.execute("SELECT fixture_id,collection_name,collection_id FROM fixture_vector_binding").fetchall()
        if (len(markers)!=1 or markers[0][0]!=fixture_id or len(rows)!=1
                or tuple(rows[0])!=(fixture_id,name,collection_id)):
            raise PermissionError("fixture identity mismatch")
        client = chromadb.PersistentClient(path=str(chroma),
                    settings=Settings(anonymized_telemetry=False))
        collection = client.get_collection(name=name, embedding_function=None)
        if _binding(conn, collection, fixture_id)!=collection_id:
            raise PermissionError("collection identity mismatch")
        return conn, client, collection
    except BaseException:
        conn.close()
        raise


def _bounded_ids(conn, table):
    rows = conn.execute("SELECT "+("id" if table=="memories" else "memory_id")+
                        " FROM "+table+" LIMIT ?", (MAX_RECORDS+1,)).fetchall()
    if len(rows)>MAX_RECORDS:
        raise ValueError("reconciliation SQL budget exceeded")
    ids={r[0] for r in rows}
    if any(type(mid) is not int or not 1<=mid<=2**63-1 for mid in ids):
        raise ValueError("invalid fixture SQL ID")
    return ids


def census(conn, collection, fixture_id):
    """Read-only logical classification under exclusive fixture ownership."""
    if conn.in_transaction:
        raise ValueError("independent census transaction required")
    with conn:
        conn.execute("BEGIN IMMEDIATE")
        cid=_binding(conn,collection,fixture_id)
        live=_bounded_ids(conn,"memories")
        intents=_bounded_ids(conn,"memory_forget_intents")
        if live & intents:
            raise RuntimeError("conflicting SQL lifecycle state")
        if collection.count()>MAX_RECORDS:
            raise ValueError("reconciliation vector budget exceeded")
        rows=collection.get(limit=MAX_RECORDS+1,include=["metadatas"])
        ids,metadata=rows.get("ids"),rows.get("metadatas")
        if (type(ids) is not list or type(metadata) is not list
                or len(ids)!=len(metadata) or len(ids)>MAX_RECORDS
                or any(type(v) is not str for v in ids)
                or len(set(ids))!=len(ids) or len(ids)!=collection.count()):
            raise RuntimeError("incomplete or invalid vector census")
        present=set()
        held=[]
        for vid,meta in zip(ids,metadata):
            if (not re.fullmatch(r"[1-9][0-9]{0,18}",vid)
                    or int(vid)>2**63-1
                    or meta!={"fixture_id":fixture_id,"native_id":vid}):
                held.append(vid)
                continue
            present.add(int(vid))
        # A mismatched record must not be mistaken for an absent vector.
        blocked={int(v) for v in held if re.fullmatch(r"[1-9][0-9]{0,18}",v)
                 and int(v)<=2**63-1}
        return {"collection_id":cid,"live_present":sorted(live & present),
                "live_missing":sorted(live-present-blocked),
                "forgotten_present":sorted(intents & present),
                "forgotten_absent":sorted(intents-present-blocked),
                "unknown_orphans":sorted(present-live-intents),
                "binding_mismatch_count":len(held),
                "authority":"NONE"}


def reconcile(conn, collection, fixture_id):
    """Explicit fixture-only retry; no unknown or mismatched IDs are deleted.

    Each eligible ID is independently revalidated by the existing adapter.
    Failure stops the batch; earlier committed observations remain durable.
    """
    before=census(conn,collection,fixture_id)
    eligible=sorted(before["forgotten_present"]+before["forgotten_absent"])
    receipts=[cleanup_fixture_vector(conn,collection,fixture_id,mid) for mid in eligible]
    return {"before":before,"receipts":receipts,
            "after":census(conn,collection,fixture_id),"authority":"NONE"}
