# Living Memory R11.2 — explicit keyring and versioned text envelopes

Base: R11.1 tested head 41801d7c88688917c369c9fbf9578a0ad0344c33.
Disposable fixture qualification only; production remains HELD.

## Contract

The previous deterministic password-derived fallback is removed. The
legacy MEMORIA_KEY setting is not used by the new encryption path.
MEMORIA_ENCRYPT_AT_REST must be exactly 0 or 1 (default 0 for compatibility).
When enabled, a nonempty explicit MEMORIA_ENCRYPTION_KEYS JSON object and
MEMORIA_ACTIVE_KEY_ID are required. Generate each distinct key independently
with cryptography.fernet.Fernet.generate_key(). Provision them through a
protected local supervisor environment or secret manager. Never commit keys,
print them in logs, send them via API requests, or use fixture keys for real data.

The envelope is memoria:v1:<key-id>:<Fernet token>. Its authenticated inner
JSON binds the schema, key ID, application and original text. Unknown keys,
legacy unversioned ciphertext, invalid tokens and application mismatch
produce the same redacted text placeholder. A missing/invalid enabled
configuration fails the HTTP request with 503 and prevents UI storage.
No silent plaintext fallback when encryption is requested.

The native SQLite schema and encrypted=1 flag are unchanged. Existing legacy
ciphertext is not decrypted, rewritten or deleted. There is no automated
migration, and the old seed must not be considered an adequate key.
Preserve legacy recovery material securely if required for a separately
reviewed migration; do not expose legacy plaintext during this experiment.

## Rotation and boundaries

Provision a new independently generated key under a fresh ID, retain old
versioned keys for reads, and change the active ID for subsequent writes.
An older record is not rewritten by rotation. Removing its key makes its
text unavailable; it does not establish physical erasure or permanent loss
if the key exists elsewhere. No online atomic rekey/rotation protocol,
external key custody, HSM or key recovery service is implemented.

Scoped HTTP reads and writes can use the configured keyring only after the
existing authentication and native permission check. The UI is still a
trusted local operator path. Its vector collection initialization, indexing
and semantic recall are suspended, as are the API vector paths. Existing
Chroma data is untouched and may contain historical plaintext. Direct
legacy vector helper calls are not disabled or qualified for use.

Encryption protects text, not tags, metadata, row identifiers, SQLite
file structure, backup artifacts or decrypted exports. The envelope binds
application identity, not row identity or all metadata. Same-app ciphertext
substitution and privileged database tampering remain outside this contract.
Plaintext mode remains available and is not a migration/downgrade operation.
An operator who sets mode 0 can deliberately write plaintext even if earlier
records are encrypted. No secure deletion or independent review claim.

## Regression expectations

Ten new methods cover missing configuration despite a legacy password,
malformed/duplicate keys, explicit mode, randomized envelopes, key rotation,
wrong keys and tampering, application substitution, preservation of legacy
ciphertext, scoped encrypted HTTP access and permission revocation.

    python -m unittest discover -s tests -v

Tests use disposable fixture databases and public deterministic fixture keys.
Existing tests continue to exercise the authorization contract.
No production key or personal database accessed. R11.3 will address private
scoped indexing and recall; R11.4 coordinated deletion and restoration.
