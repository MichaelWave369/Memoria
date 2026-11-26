# GenomeMemory native fixture export v1

Owner: Memoria. Native schema base: 9c480fcaea467615252d347956eac42ff038edf7.
The explicit local Python interface creates a new disposable source DB with
the existing db.storage.init_db schema. It exports only the seven metadata
columns accepted by PhiMemory9's R0.4 adapter, preserving native integer IDs.
Native can_read=1 must exist for the exact application at the time of export.
No content, arbitrary metadata, key material or vectors are selected.
Existing files and unmarked databases are refused; no API endpoint is added.

Run: `python -m unittest discover -s tests -v` (existing cryptography dependency).
The PhiMemory9 native demonstration separately calls the existing store_memory
and set_permission functions, this exporter, then held-only R0.4 staging.
Export permission is not expression consent or proof of metadata truth.

## Security blockers confirmed in native source

Read/semantic/synthesis/delete/permission API routes lack authenticated caller
enforcement; can_read is not enforced there. Unknown apps can write by default.
The fallback encryption key is deterministically derived from a fixed seed;
truncation/padding is not a secure key-management design. The vector collection
stores plaintext document content even if SQL content is encrypted. SQL delete
does not delete vector entries. These findings remain unresolved by this
additive exporter. Keep real memory bridges blocked pending coordinated API,
key, indexing and deletion work. Do not run the API for this experiment.

The local connection and operator are trusted. Fixture markers can be forged
by a process with source DB write access; they are accidental-use guardrails.
Tests use newly created synthetic databases exclusively.

