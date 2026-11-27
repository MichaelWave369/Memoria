# Living Memory R11.1 — local application API authorization

> Historical milestone: encryption, recall and deletion behavior below describes R11.1 at its original revision. For the current interface see [README](../README.md), [R11.2](LIVING_MEMORY_R11_KEYRING.md), [R11.3a](LIVING_MEMORY_R11_PRIVATE_RECALL.md), and [R11.4a](LIVING_MEMORY_R11_FORGET_INTENT.md).

Base 48ec222d39f1fcc4b54cf99b6fcd2b15be1a1be8. Source inspection of
backend/api.py, db/storage.py, db/vector_store.py, streamlit_app.py and
integrations/triad_hooks.py confirms missing authenticated read/synthesis/
semantic/delete/permission boundaries, default-open unknown writes and an
embedded API bound to all interfaces. These are source findings, not
evidence of actual disclosure. Production remains HELD.

## Application boundary

The API no longer opens SQLite or Chroma at import. Per-request connection
ownership and BEGIN IMMEDIATE serialize native explicit read/write
permission checks with the selected SQL operation. The caller's bearer
credential resolves to exactly one application; the app_name parameter
cannot impersonate another app. Missing scope defaults to caller scope,
not all applications. Synthesis reads only tags within caller scope.
Unknown/missing permission rows deny. The native storage functions and
fixture export contract remain unchanged.

The operator must supply MEMORIA_API_TOKEN_SHA256 as a JSON object mapping
exact app names (case-sensitive) to SHA-256 digests of independently
generated high-entropy random bearer tokens. Use an approved local secret
manager or a protected supervisor environment. Generate each token with
Python secrets.token_urlsafe(32) or equivalent and hash its ASCII bytes
using hashlib.sha256(...).hexdigest(). Do not commit, print in logs or
transmit tokens through URLs. There are no built-in/default credentials,
no password stretching for human passwords, no web provisioning route.
The registry rejects duplicate entries/digests, invalid shapes and absent
configuration; its hashes assume randomly generated credentials, not
passwords. Configure both an application credential and explicit native
can_read/can_write flags via the trusted local operator, then restart or
reconfigure the supervisor when rotating credentials.

The local client accepts token= explicitly and sends it only in the
Authorization header to a local HTTP endpoint; redirects and environment
proxies are disabled. Use 127.0.0.1 rather than relying on hostname resolution.
The embedded API and default Streamlit configuration bind to loopback.
Do not override these bindings or proxy them onto a network.

## Deliberate compatibility changes

- Query and synthesis require scoped read permission; query limits 1..500.
- Store requires scoped write permission. Stores plaintext SQL only if
  encryption is not requested; no vector upsert, index_status HELD.
- Encrypted rows return the existing storage redaction placeholder. No
  API cipher use while the legacy key path is unqualified.
- If encryption is requested, API writes return 503 rather than silently
  storing plaintext. No re-encryption or key migration.
- Semantic search, delete and permission management HTTP routes return
  503 after caller authentication, without performing the operation.
  Missing or invalid credential returns 401, missing/malformed registry
  returns 503, denied scope or policy returns 403.
- Health remains public and contains no database data.
- Existing callers must be updated to supply a token; old unauthenticated
  clients are intentionally no longer supported. UI synthesis no longer
  makes an unauthenticated app request.

## Reproduction and limits

Eleven FastAPI TestClient methods use only disposable local SQLite data,
no vector server or real credentials. CI installs FastAPI/httpx alongside
the existing fixture-export dependencies. Run:

    python -m unittest discover -s tests -v

This is local API containment, not a complete source security qualification.
The trusted operator UI and direct storage access can still see/write all
records, retain legacy key derivation, index plaintext and leave vector
copies after SQL deletion. Do not use sensitive data or claim complete
forgetting. Default app-permission schema values are not changed; this API
requires explicit existing rows and does not create them. Credentials
are operator-configured, not an externally verified identity; no TLS,
credential lifecycle service, rate limiting, payload-size budget,
multi-host threat model, independent reviewer or full concurrency proof.
Configuration reload between requests is not an atomic external revocation
protocol. The direct UI's local-only configuration is a default, not
an authentication barrier.

R11.2: key management and encrypted storage qualification; R11.3: scoped
vector indexing and recall; R11.4: coordinated deletion and recovery.
No live databases migrated or accessed. The PhiMemory9 native bridge
remains fixture-only and held for production.
