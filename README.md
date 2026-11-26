# 🧠 Memoria v0.1 — The Eternal Memory Vault

> A beautiful, 100% local and private persistent memory layer for the entire Triad369 ecosystem.

![hero screenshot placeholder](docs/screenshots/hero-placeholder.png)

Memoria gives Agentora, Growora, Mindora, Reconnect, CoEvo, and future Triad apps a shared long-term memory vault with structured storage, semantic recall, and growth synthesis — all fully offline.

## Highlights

- **No cloud, no telemetry, no external data services**
- **Streamlit-first noir UI** + embedded **FastAPI** backend
- **SQLite + Chroma vector store** (lightweight, local)
- Local embeddings via **Ollama** (`nomic-embed-text`) with deterministic local fallback
- Permission controls per app (read/write)
- Export as `.memoria` vault file
- “Forget” sensitive memories in one click
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
# Semantic recall is held pending scoped vector privacy review.
```

## API Endpoints

- `POST /memoria/store`
- `GET /memoria/query`
- `POST /memoria/semantic`
- `GET /memoria/synthesis?window=daily|weekly`
- `POST /permissions/{app_name}?can_read=true&can_write=false`
- `GET /health`

## Data-at-rest encryption option

Legacy operator-only encryption option (not qualified for real sensitive data). The API holds encrypted writes and redacts encrypted text until the next key-management milestone:

```bash
export MEMORIA_ENCRYPT_AT_REST=1
export MEMORIA_KEY="your-local-secret"
```

## Triad369 Launchpad registration

Use `launchpad/apps.toml.snippet` as your app registration base.

## Screenshots

- Dashboard placeholder: `docs/screenshots/dashboard-placeholder.png`
- Explorer placeholder: `docs/screenshots/explorer-placeholder.png`

## License

MIT
