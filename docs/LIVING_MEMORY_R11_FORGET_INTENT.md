# Living Memory R11.4a — durable logical deletion intent

Base: Memoria main 4c9166ec978ba0fed384b3aad3ba50ff78f759d1, with
R11.3c/d merged. Disposable fixture qualification only; production HELD.

## Source findings and correction

db/storage.py previously deleted only the memories row and committed.
The direct operator UI advertised permanent forgetting despite legacy
Chroma copies and untracked backups/exports. HTTP deletion and vector
recall were already held in R11.1–R11.2 and remain held.

The native initializer now installs an additive memory_forget_intents
table and three triggers. An ordinary SQL DELETE from memories records
its native integer ID in the same transaction, with vector_state
PENDING_UNVERIFIED and external_state UNKNOWN. No payload, app name,
tags, key or original metadata are copied into the ledger. A trigger
failure rolls back the delete. Forgotten IDs cannot be inserted again
or assigned by updating a live record's ID while these triggers and
the ledger remain intact. Native auto-increment remains unchanged.

delete_memory owns an independent BEGIN IMMEDIATE transaction and
refuses to commit caller-owned work. It validates positive SQLite
integer IDs and refuses to commit a newly deleted row without its
cleanup intent. Repeating deletion of an already-tombstoned record
returns the original minimal status; an unknown ID returns NOT_FOUND
and does not manufacture a tombstone. A returned LOGICALLY_DELETED
receipt means the primary row is absent under the current trusted
database state, not a proof of external erasure. No receipt grants
authority. Fixed CHECK constraints intentionally do not allow a
VERIFIED cleanup label at this milestone.

The trusted operator UI requires explicit confirmation, uses a fresh
connection for deletion, reports remaining obligations and reruns
to refresh its own displayed SQL snapshot. Other sessions and
previously downloaded exports may retain earlier data. This UI
does not represent authenticated application-level deletion consent.
The existing HTTP delete route remains held.

## Verification

    python -m unittest discover -s tests -v

Twelve new disposable SQLite methods check atomic intent, reopen and
repeat behavior, unknown IDs, direct SQL rollback/commit, missing or
failing trigger, explicit ID resurrection, unrelated transaction
protection, scoped recall exclusion, payload-free ledger columns,
fixed uncertainty states, and invalid IDs. Existing R11 tests remain
in the suite. No Chroma service, model call, live data or physical
disk wiping experiment.

## Remaining gates

Historical deletes before installation cannot be reconstructed from
this ledger. On first launch the initializer creates the new schema;
no live database has been opened or migrated in this work. Existing
or incompatible same-name schema objects are not independently
attested. Deployment would require a reviewed schema migration and
exclusive maintenance boundary, not concurrent legacy writers.
This is ordinary SQL/API behavior, not a hostile database sandbox:
privileged SQL, trigger removal, replacement semantics, ledger
tampering, file restoration and reuse of IDs in another database
are outside this guarantee. Restoring the whole database can restore
both a record and absence of its intent; external continuity is an
open gate. Native IDs are database-local, not globally unique.

No physical erasure, secure RAM wiping, export revocation, backup
destruction, real Chroma deletion, or persistent authenticated
derivative relationship registry is implemented. The offline
relationship experiments have no live relationship records to clean.
Historical plaintext vector collections remain held and untouched.
The ledger contains an ID and state only, and therefore does not
claim to identify every copy or establish provenance for an existing
legacy Chroma collection.

Next R11.4b: explicitly bound disposable native vector collection
cleanup adapter, verification of absence and idempotent retry;
R11.5: interruption/restart and orphan reconciliation. Production
and live cross-repository bridges remain HELD.
