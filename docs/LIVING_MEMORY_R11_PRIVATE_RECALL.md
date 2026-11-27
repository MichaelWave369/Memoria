# Living Memory R11.3a — bounded private lexical recall

Base: green R11.2 head ae1009eaa1c1064293cc188b089c193059b8937d.
This is a lexical baseline, not semantic embeddings or production qualification.

## Contract

POST /memoria/recall accepts only text (1..512 characters, at most 64 distinct
case-folded Unicode alphanumeric terms) and integer limit (1..20, default 5).
Caller scope comes exclusively from the bearer credential and current native
read permission. Query, length preflight, decrypt and ranking use the existing
serialized SQLite transaction. Reject invalid request fields and missing
permission. Refuse scopes exceeding 256 rows, 65,536 stored bytes per row,
or 2 MiB aggregate stored bytes; no partial ranking on overflow. The size
limits apply to stored bytes including ciphertext, not a universal CPU or
memory bound. SQL may still scan a larger table.

Each readable record is tokenized in the process and scored by exact
Jaccard overlap: intersection cardinality divided by union cardinality.
Only positive matches are returned, sorted descending by exact rational
score then ascending native record ID. Unreadable encrypted records,
legacy ciphertext, invalid flags and the encrypted redaction sentinel
are excluded. A legitimate encrypted text exactly equal to that sentinel
is conservatively excluded. No stemming, semantic inference, learned
model or retrieval superiority claim.

Response contains method, item IDs and reduced rational scores, and
authority NONE. No raw content, query echo, tags, metadata or snippets.
IDs and scores are still sensitive derived information and must be
handled within the same application trust boundary. The existing
scoped query endpoint remains available for authorized text retrieval.

There is no vector creation, model call, persistent token cache or
secondary plaintext index. Legacy /memoria/semantic remains held.
The client offers recall() separately; no silent change of semantic
endpoint meaning. UI legacy vector paths remain suspended.
A deleted SQL row disappears from this path without index maintenance,
but that is not physical deletion or reconciliation of historical copies.

## Verification

    python -m unittest discover -s tests -v

Twelve added methods cover exact ranking, ties, authentication, scope,
permission withdrawal, encrypted and legacy rows, Unicode and abstention,
row/byte budgets, strict request schema, logical read-only behavior and
held legacy semantic route. All use disposable fixtures.

## Remaining gates

No secure RAM wiping, access-pattern privacy, hostile host protection,
full-file encryption, persistent private embeddings, external key custody,
complete deletion, or independent audit. Decrypted values exist in process
memory during ranking. Repeated authorized searches may reveal information
via scores. HTTP request/body limits and rate controls need separate work.
This prototype cannot serve arbitrarily large vaults. SQLite's write lock
is held during scoring; measure contention before scaling. Old Chroma files
are untouched and may still contain plaintext. Production remains HELD.
Next: R11.3b controlled retrieval-quality and cost comparison, then scoped
semantic feasibility and coordinated deletion/recovery.
