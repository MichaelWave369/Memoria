"""R11.6 held-only fixture handoff; no runtime or production qualification."""
import hashlib
import json

from db.genomememory_export import export_fixture_metadata, SOURCE_REVISION

SCHEMA = "memoria-r11-fixture-handoff/v1"
AUDITED_BASE = "3967a22b650d41a16af09ff061c42ecbdec2de04"
BLOCKERS = (
    "independent_security_review",
    "live_source_permission_and_consent",
    "external_key_custody",
    "legacy_vector_and_external_copy_coverage",
    "independent_rollback_witness",
    "complete_content_integrity",
    "runtime_authority_mapping",
)


def commitment(snapshot):
    raw = json.dumps(snapshot, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=True, allow_nan=False).encode("ascii")
    if len(raw) > 1024 * 1024:
        raise ValueError("fixture export byte budget")
    return hashlib.sha256(b"memoria-r11-fixture-handoff/v1\0" + raw).hexdigest()


def handoff(conn, *, expected_app, fixture_id):
    """Only existing synthetic fixtures, with explicit native read permission.

    Lock permission lookup and metadata read together. The legacy snapshot
    remains unchanged so the existing PhiMemory9 adapter can consume it.
    The outer receipt is not authenticated, nor proof of checkout identity.
    """
    if conn.in_transaction:
        raise ValueError("independent fixture handoff transaction required")
    with conn:
        conn.execute("BEGIN IMMEDIATE")
        snapshot = export_fixture_metadata(conn, expected_app=expected_app,
                                          fixture_id=fixture_id)
        digest = commitment(snapshot)
    return {"schema": SCHEMA, "synthetic": True, "authority": "NONE",
            "status": "HELD", "live_ready": False,
            "audited_base": AUDITED_BASE,
            "legacy_adapter_revision": SOURCE_REVISION,
            "snapshot_sha256": digest, "snapshot": snapshot,
            "blockers": list(BLOCKERS)}
