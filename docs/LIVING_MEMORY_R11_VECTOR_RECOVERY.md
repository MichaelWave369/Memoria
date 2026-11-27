# Living Memory R11.5a — native cold-restart and orphan reconciliation

Base: main d284144123c4bdc47d14c95b5f26e8a6aa8f84a2, green #11.
Disposable synthetic fixtures only. Authority NONE; production HELD.

## Cold reopen

A caller supplies the existing fixture root, exact fixture ID and expected
collection UUID. The opener refuses missing paths, direct symlink paths,
and mismatched SQLite markers/bindings before opening the native
collection by name. It uses get_collection, not get_or_create_collection,
and rechecks the native collection identity and metadata. SQLite is
opened in existing read/write mode without calling the schema initializer.
This is a trusted local fixture guardrail, not path confinement or
cryptographic authentication. Chroma itself may perform normal storage
initialization/recovery on reopen.

## Bounded census

Under exclusive fixture ownership, take a serialized SQL snapshot and
enumerate up to 256 live SQL IDs, 256 durable forget IDs and 256 native
vector IDs/metadata. Refuse over-budget or malformed census results
before cleanup; do not silently truncate. Refuse overlapping live and
forgotten SQL IDs. Compare native decimal IDs and exact per-record fixture
metadata. Report live vectors, live records without a vector, forgotten
vectors still present, forgotten IDs whose vector is absent, unknown
orphans and a count of mismatched bindings. A mismatched vector ID is
not treated as absent. No documents, embedding values or mismatched
raw IDs are returned. A census does not mutate the logical ledger or
delete anything, though opening the native engine may change its files.

Explicit reconcile reruns the existing R11.4b cleanup adapter only for
forgotten-present and forgotten-absent IDs, including those with a prior
observation. Revalidate each target before acting. Do not recreate missing
live vectors, delete unknown orphans or touch mismatched vector records.
Each cleanup has its own transaction: a failed batch may have earlier
committed observations and can be retried. This is not a distributed
atomic batch. An observed absence is collection-specific, not proof
of all copies being removed. The original forget intent remains
PENDING_UNVERIFIED / UNKNOWN.

## Fresh-process verification

Six opt-in test methods use subprocesses that create, reopen, inspect and
reconcile actual persistent Chroma fixtures. Every worker has a fresh
interpreter, with no inherited Chroma client. Two deliberate os._exit(91)
boundaries terminate after the pending SQL observation was committed but
before native deletion, and after a native delete returns but before
recording absence. The latter test expects the acknowledged delete to
remain visible on cold reopen; a failure is evidence, not grounds for
silently weakening the expectation. Additional controls check stale
reintroduction, unrelated orphan/mismatched records, missing live
vectors, an incorrect collection UUID and SQL budget refusal. The
native job remains pinned to Chroma 1.0.20 and runs both test modules.

    MEMORIA_NATIVE_CHROMA_FIXTURES=1 ANONYMIZED_TELEMETRY=False python -m unittest discover -s tests -p 'test_native_vector_recovery_r11.py' -v

No native pass is claimed until CI actually runs. Abrupt exit is at
specific Python/native API boundaries, not arbitrary internal database
commit interruption, power loss or hardware durability qualification.

## Unresolved

No concurrent Chroma writer protocol, hostile filesystem defense,
legacy collection adoption, global identity, authenticated external
retention ledger, automatic startup job, full physical erasure or
rollback of the entire paired store. Unknown or mismatched records
are held by classification, not physically isolated from privileged
direct vector access. The legacy semantic endpoint stays held. No
live personal data accessed. Next: test stale observations and
rollback boundaries, independent source qualification and the
cross-repository retention bridge.
