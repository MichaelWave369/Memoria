# 🧠 Memoria v0.1 — The Eternal Memory Vault

> An experimental local-first persistent memory layer for the Triad369 ecosystem.

![hero screenshot placeholder](docs/screenshots/hero-placeholder.png)

Memoria gives Agentora, Growora, Mindora, Reconnect, CoEvo, and future Triad apps a shared long-term memory vault with structured storage and scoped synthesis. Semantic recall remains held during security hardening.

## Highlights

- **No cloud, no telemetry, no external data services**
- **Streamlit-first noir UI** + embedded **FastAPI** backend
- **SQLite storage** with optional versioned text encryption
- Chroma/Ollama legacy paths held pending private indexing review
- Permission controls per app (read/write)
- Export as `.memoria` vault file
- Local SQL deletion with durable cleanup intent; historical vectors and external copies remain unverified
- Launchpad-ready snippet included

## One-command install

```bash
python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && streamlit run streamlit_app.py
```

## Project Structure

```text
streamlit_app.py
backend/
  api.py
db/
  storage.py
  vector_store.py
  models.py
integrations/
  triad_hooks.py
launchpad/
  apps.toml.snippet
```

## R11.1 local application API (security candidate)

The application API now requires an explicit per-app bearer credential and a native permission row. It is not production-qualified. See [the scoped API protocol](docs/LIVING_MEMORY_R11_API_SCOPE.md) for provisioning, compatibility changes and held routes. The direct operator UI remains a separate trusted-local path; do not expose it to a network.

## How it connects to Agentora

Agentora can call Memoria directly:

```python
from integrations.triad_hooks import MemoriaClient

import os

client = MemoriaClient("http://127.0.0.1:8765", token=os.environ["AGENTORA_MEMORIA_TOKEN"])

client.store(
    content="User prefers concise coaching prompts.",
    app_name="Agentora",
    agent_id="coach-01",
    tags=["preference", "coaching"],
    importance_score=0.9,
)

memories = client.query(app_name="Agentora", agent_id="coach-01", limit=10)
matches = client.recall("coaching prompts", limit=5)
# Lexical baseline; semantic recall remains held.
```

## API Endpoints

- `POST /memoria/store`
- `GET /memoria/query`
- `POST /memoria/recall` — bounded scoped lexical retrieval (IDs and rational scores)
- `POST /memoria/semantic` — held
- `GET /memoria/synthesis?window=daily|weekly`
- `POST /permissions/{app_name}?can_read=true&can_write=false`
- `GET /health`

## Private recall research baseline

The new lexical route scans only authorized application records within explicit research budgets, without a persistent vector index or model call. See [R11.3a protocol](docs/LIVING_MEMORY_R11_PRIVATE_RECALL.md). Production remains HELD.

## Data-at-rest encryption option

R11.2 requires explicitly provisioned, randomly generated Fernet keys. Configure the following through a protected local supervisor environment or secret manager:

- `MEMORIA_ENCRYPT_AT_REST=1`
- `MEMORIA_ENCRYPTION_KEYS`: JSON object mapping key IDs to canonical URL-safe base64 Fernet keys
- `MEMORIA_ACTIVE_KEY_ID`: the ID used for new writes

Generate keys using `cryptography.fernet.Fernet.generate_key()`. Do not reuse the old `MEMORIA_KEY` password or commit secrets. Existing legacy ciphertext is preserved and redacted; no automatic migration occurs. Text encryption does not encrypt tags, metadata, SQLite files or backups. API and operator UI vector indexing/recall are held.

See [R11.2 encryption contract](docs/LIVING_MEMORY_R11_KEYRING.md) for rotation, provisioning, and limitations. Production remains HELD.

## Triad369 Launchpad registration

Use `launchpad/apps.toml.snippet` as your app registration base.

## Screenshots

- Dashboard placeholder: `docs/screenshots/dashboard-placeholder.png`
- Explorer placeholder: `docs/screenshots/explorer-placeholder.png`

## License

MIT
