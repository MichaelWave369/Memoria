# Living Memory R11.4b — bound native vector cleanup experiment

Base: main 9665542831e4f4a55974ad91b9449bc1bcfacc36 after green #10.
Disposable synthetic fixtures only. Production HELD.

## Contract

The fixture factory creates a previously nonexistent directory, a native
SQLite fixture with a fresh random fixture marker and a local persistent
Chroma collection with no embedding function. It binds the SQL marker,
collection name and native collection UUID, and checks the collection's
fixture metadata before cleanup. It never adopts an existing directory
or uses the default Memoria or Chroma paths. Tests seed invented text
and explicit three-dimensional vectors; no Ollama or network model call.

Cleanup requires a positive native integer ID, an independent transaction,
the exact fixture binding, an absent primary SQL row, and the existing
durable forget intent. It commits a separate PENDING_UNVERIFIED observation
before performing the native vector operation. Under the next SQL write
transaction it rechecks eligibility, gets only the requested ID and its
binding metadata, refuses mismatched records, deletes that exact vector ID
if present, and performs a fresh native get to verify logical absence.
Only then does it commit ABSENT_OBSERVED for that collection UUID.
No vector payload is returned. Repeated cleanup on an already absent ID
does not call delete again. A lost acknowledgement, no-op deletion or
failed verification leaves the observation pending; retry can inspect
the current collection again.

The primary memory_forget_intents ledger is deliberately unchanged:
vector_state PENDING_UNVERIFIED, external_state UNKNOWN. An observed
absence in a single collection is not verification of all vectors or
copies. A separate observation is a last successful logical check,
not a permanent guarantee. Unrelated live rows and collections are
not cleanup targets. No HTTP or operator UI cleanup endpoint is enabled.

## Native verification

Eight opt-in unittest methods use real PersistentClient collections in
new temporary directories and check delete/retry, primary presence and
missing intent, wrong collection/fixture, mismatched record metadata,
no-op deletion after a stale entry returns, lost acknowledgement after
actual native deletion, existing path/caller transaction refusal and
reopened SQLite observation persistence. Two fault wrappers deliberately
alter the delete call's behavior; the collection get/upsert and successful
delete operations remain native. Normal tests skip these methods unless
MEMORIA_NATIVE_CHROMA_FIXTURES=1.

Dedicated CI job: Python 3.11, chromadb==1.0.20, cryptography>=43.
Anonymized telemetry disabled in settings and CI environment; explicit
vectors avoid embedding downloads. Dependencies beyond the Chroma pin
are not fully locked. Run in a disposable environment:

    python -m pip install 'cryptography>=43' 'chromadb==1.0.20'
    MEMORIA_NATIVE_CHROMA_FIXTURES=1 python -m unittest discover -s tests -p 'test_native_vector_cleanup_r11.py' -v

No native test results are asserted until the job actually executes.

## Boundaries

Trusted exclusive fixture owner, not hostile handle or database defense.
The marker and UUID binding are accidental-misrouting controls, not
authentication. No concurrent vector writers or guarantee against
reintroduction after the check. SQL and Chroma do not share an atomic
commit; pending/retry records the gap but cannot prevent external
mutation. No fresh-process reopening of the persistent Chroma store,
arbitrary crash/power-loss, orphan census, restored SQL/Chroma pair or
external rollback qualification yet. The reopened SQL test does not
prove a cold-start vector check. No live legacy collection discovery,
adoption, deletion or migration. Existing Chroma may retain plaintext,
physical segments, transaction history, backups or exported copies.
No physical erasure, secure memory wiping or production security claim.

Next R11.5: subprocess interruption, cold reopen and bounded orphan
reconciliation of this disposable native pair; then reviewed legacy
binding and source integration remain separate gates.
