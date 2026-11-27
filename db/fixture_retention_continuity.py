"""Keyed retention topology commitment, not a full database commitment.

Uses the native fixture census under exclusive local ownership.
No payload, embedding, key, or raw IDs leave this function.
"""
import hashlib
import hmac
import json

from db.fixture_vector_recovery import census, MAX_RECORDS

SCHEMA = "memoria-retention-continuity/v1"


def snapshot(conn, collection, fixture_id, key):
    if type(key) is not bytes or len(key) != 32:
        raise ValueError("explicit 32-byte fixture key required")
    topology = census(conn, collection, fixture_id)
    if topology["binding_mismatch_count"]:
        raise ValueError("unqualified vector binding in continuity census")
    # Census and observation read are separate SQL transactions. Exclusive
    # fixture ownership is a precondition; this is not concurrent snapshotting.
    with conn:
        conn.execute("BEGIN IMMEDIATE")
        rows = conn.execute(
            "SELECT memory_id,collection_id,state FROM fixture_vector_observations "
            "ORDER BY memory_id LIMIT ?", (MAX_RECORDS+1,)).fetchall()
        if len(rows)>MAX_RECORDS:
            raise ValueError("continuity observation budget exceeded")
        known = set(topology["forgotten_present"]+topology["forgotten_absent"])
        for mid,cid,state in rows:
            if mid not in known or cid!=topology["collection_id"] or state not in (
                    "PENDING_UNVERIFIED","ABSENT_OBSERVED"):
                raise ValueError("invalid continuity observation")
        body = {"fixture_id":fixture_id,"topology":topology,
                "observations":[list(r) for r in rows]}
        raw = json.dumps(body,sort_keys=True,separators=(",",":"),
                         ensure_ascii=True,allow_nan=False).encode("ascii")
        digest = hmac.new(key, b"memoria-retention-continuity/v1\0"+raw,
                          hashlib.sha256).hexdigest()
    return {"schema":SCHEMA,"synthetic":True,"authority":"NONE",
            "witness_sha256":digest}


def compare(record, pin):
    if (type(record) is not dict or set(record)!={"schema","synthetic","authority","witness_sha256"}
            or record["schema"]!=SCHEMA or record["synthetic"] is not True
            or record["authority"]!="NONE"):
        raise ValueError("invalid retention snapshot")
    for digest in (record["witness_sha256"],pin):
        if type(digest) is not str or len(digest)!=64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("invalid retention digest")
    return {"matches":hmac.compare_digest(record["witness_sha256"],pin),
            "authority":"NONE","status":"HELD"}
