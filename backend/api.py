"""Local application API; direct operator UI/storage are separate trust paths."""
import json
from contextlib import closing, contextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field

from backend.access import ConfigurationError, authenticate, permitted
from db.storage import get_connection, query_memories, store_memory
from db.keyring import KeyConfigurationError, configured_cipher

app = FastAPI(title="Memoria API", version="0.1.1")


class MemoryIn(BaseModel):
    content: str
    app_name: str
    agent_id: str = "unknown"
    timestamp: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    importance_score: float = 0.5
    metadata: Dict[str, Any] = Field(default_factory=dict)


class QueryIn(BaseModel):
    text: str
    limit: int = 5


def caller(authorization: Optional[str] = Header(default=None)) -> str:
    try:
        return authenticate(authorization)
    except ConfigurationError:
        raise HTTPException(status_code=503, detail="Application API not configured") from None
    except PermissionError:
        raise HTTPException(status_code=401, detail="Application authentication required",
                            headers={"WWW-Authenticate": "Bearer"}) from None


def scope(requested, principal):
    if requested is not None and requested != principal:
        raise HTTPException(status_code=403, detail="Application scope denied")
    return principal


@contextmanager
def authorized(principal, operation):
    # Permission and SQL operation share the same serialized transaction.
    # Each request owns its connection; no shared global SQLite connection.
    with closing(get_connection()) as conn:
        with conn:
            conn.execute("BEGIN IMMEDIATE")
            if not permitted(conn, principal, operation):
                raise HTTPException(status_code=403, detail="Application permission denied")
            yield conn


def request_cipher():
    try:
        return configured_cipher()
    except KeyConfigurationError:
        raise HTTPException(status_code=503, detail="Encryption configuration unavailable") from None


def held():
    raise HTTPException(status_code=503, detail="Operation held pending storage security review")


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "service": "memoria"}


@app.post("/memoria/store")
def memoria_store(memory: MemoryIn, principal: str = Depends(caller)) -> Dict[str, Any]:
    scope(memory.app_name, principal)
    with authorized(principal, "write") as conn:
        cipher = request_cipher()
        new_id = store_memory(conn, memory.model_dump(), cipher=cipher)
    # Indexing is deliberately deferred until scoped, private indexing exists.
    return {"id": new_id, "status": "stored", "index_status": "HELD"}


@app.get("/memoria/query")
def memoria_query(
    app_name: Optional[str] = None,
    agent_id: Optional[str] = None,
    tag: Optional[str] = None,
    since: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
    principal: str = Depends(caller),
) -> Dict[str, Any]:
    app_name = scope(app_name, principal)
    with authorized(principal, "read") as conn:
        cipher = request_cipher()
        memories = query_memories(conn, app_name=app_name, agent_id=agent_id,
                                  tag=tag, since=since, limit=limit, cipher=cipher)
    return {"count": len(memories), "items": memories}


@app.post("/memoria/semantic")
def memoria_semantic(query: QueryIn, principal: str = Depends(caller)):
    held()


@app.delete("/memoria/{memory_id}")
def memoria_delete(memory_id: int, principal: str = Depends(caller)):
    held()


@app.get("/memoria/synthesis")
def memoria_synthesis(window: str = "daily", principal: str = Depends(caller)):
    if window not in ("daily", "weekly"):
        raise HTTPException(status_code=422, detail="Invalid synthesis window")
    since = (datetime.utcnow() - timedelta(days=1 if window == "daily" else 7)).isoformat()
    with authorized(principal, "read") as conn:
        rows = conn.execute(
            "SELECT tags FROM memories WHERE app_name=? AND timestamp>=? "
            "ORDER BY timestamp DESC LIMIT 500", (principal, since)).fetchall()
        tags: Dict[str, int] = {}
        for row in rows:
            for tag in json.loads(row["tags"]):
                tags[tag] = tags.get(tag, 0) + 1
    return {"summary": {"window": window, "total_memories": len(rows),
                        "top_apps": [(principal, len(rows))] if rows else [],
                        "top_tags": sorted(tags.items(), key=lambda x: x[1], reverse=True)[:5]}}


@app.get("/permissions")
def permissions_list(principal: str = Depends(caller)):
    held()


@app.post("/permissions/{app_name}")
def permissions_set(app_name: str, can_read: bool = False, can_write: bool = False,
                    principal: str = Depends(caller)):
    held()
