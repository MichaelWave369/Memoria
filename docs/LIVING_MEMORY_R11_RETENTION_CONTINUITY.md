# Living Memory R11.5b — retention topology continuity

Base: Memoria main a7398bcea1a0a422895ce4fae783041d35af2d18, green #12.
Disposable synthetic fixtures only. Production HELD; authority NONE.

## Scope

The bounded native R11.5a census supplies live/forgotten ID partitions,
vector presence and unknown orphan IDs. Refuse mismatched vector binding,
invalid observation state or observation scope. Include the fixture ID,
collection UUID and sorted cleanup observations. HMAC-SHA256 over the
canonical ASCII JSON with a separate domain memoria-retention-continuity/v1
and an explicit 32-byte fixture key yields a retention topology commitment.
The snapshot returns only schema, synthetic marker, authority and digest.
No raw IDs, content, metadata, vectors or key are exported by this function.
The census and observation read are separate transactions, so exclusive
fixture ownership remains a precondition. No concurrent snapshot claim.

This is a deliberately narrower commitment than PhiMemory9's logical
database snapshot. It does NOT authenticate all content, metadata, permissions,
embeddings, schema, physical storage or external copies. A same-ID text
edit is intentionally undetected; the negative control records that limit.
The compare function reports advisory equality only, always HELD. A
matching pin is not permission to recall or delete information.

## Native cross-repository reuse

Reuse the existing PhiMemory9 scripts/living_native_continuity.mjs at
d897308cb0af166bda9c897eac6ed03d8958577d without rewriting its protocol.
That script invokes the actual NBGPocketMesh native R11 anchor at
0687f10970989194d4af554d9b189c7ce8a1ad15. The new test supplies digests
from the actual cold-restored older Memoria pair and the newer forgotten
state. The nine upstream checks cover initial/latest attestations,
older and wrong-epoch/digest states, nonce mismatch, wrong key, altered
statement and rejected nonmonotonic promotion. The epoch is supplied
by the fixture harness, not persisted in Memoria. The anchor is initialized
and advanced explicitly inside that harness; it is not an always-on
service that observed the deletion in real time. No duplicate signing
implementation, runtime gate, automatic promotion or off-host service.

## Tests

Seven opt-in native methods use separate fresh subprocesses and copy
only closed disposable fixture directories. They compare current state
and wrong key; restore the entire pair, just SQL, or just Chroma; preserve
the content-edit blind spot; refuse bad vector binding; and exercise the
nine upstream anchor assertions against actual Memoria digests.
Full restore returns the old digest and disagrees with the newer retained
pin. Restoring the pin too defeats this equality check by construction.
No actual live memory files are touched.

Dedicated CI uses the existing Chroma 1.0.20 job, Node 20, and the exact
two upstream revisions. Set MEMORIA_NATIVE_CHROMA_FIXTURES=1 and the
MEMORIA_NATIVE_PHI_MEMORY / MEMORIA_NATIVE_POCKETMESH environment variables
to the respective pinned checkout paths to reproduce:

    python -m unittest discover -s tests -p 'test_native_retention_continuity_r11.py' -v

The cross-repository test skips without both checkout paths. Native job
supplies both. CI must execute before any pass claims.

## Remaining gates

Independent operator custody, authenticated epoch binding, external
witness availability and rollback resistance, concurrency, restoration
of key material, authenticated deletion consent, complete content
integrity, actual legacy collection adoption and external copy retention
remain unqualified. The fixture key is public test material. The upstream
anchor runs locally with a same-process verifier/server in the native
Node harness, not an independently administered authority. No secure
physical erasure or power-loss claim. No runtime API or production bridge
changes. Next: R11.6 source qualification and cross-repository handoff.
