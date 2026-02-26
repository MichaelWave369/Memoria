import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from db.storage import (
    delete_memory,
    get_cipher,
    get_connection,
    get_permissions,
    query_memories,
    set_permission,
    store_memory,
)
from db.vector_store import get_collection, query_similar, upsert_memory

app = FastAPI(title="Memoria API", version="0.1.0")
conn = get_connection()
collection = get_collection()


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


def _can_write(app_name: str) -> bool:
    rules = {row["app_name"]: row for row in get_permissions(conn)}
    if app_name not in rules:
        return True
    return bool(rules[app_name]["can_write"])


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "service": "memoria"}


@app.post("/memoria/store")
def memoria_store(memory: MemoryIn) -> Dict[str, Any]:
    if not _can_write(memory.app_name):
        raise HTTPException(status_code=403, detail="Write permission denied")
    cipher = get_cipher(os.getenv("MEMORIA_ENCRYPT_AT_REST", "0") == "1")
    payload = memory.model_dump()
    new_id = store_memory(conn, payload, cipher=cipher)
    upsert_memory(collection, new_id, memory.content, {"app_name": memory.app_name, "agent_id": memory.agent_id})
    return {"id": new_id, "status": "stored"}


@app.get("/memoria/query")
def memoria_query(
    app_name: Optional[str] = None,
    agent_id: Optional[str] = None,
    tag: Optional[str] = None,
    since: Optional[str] = None,
    limit: int = 100,
) -> Dict[str, Any]:
    cipher = get_cipher(os.getenv("MEMORIA_ENCRYPT_AT_REST", "0") == "1")
    memories = query_memories(conn, app_name=app_name, agent_id=agent_id, tag=tag, since=since, limit=limit, cipher=cipher)
    return {"count": len(memories), "items": memories}


@app.post("/memoria/semantic")
def memoria_semantic(query: QueryIn) -> Dict[str, Any]:
    return {"items": query_similar(collection, query.text, query.limit)}


@app.delete("/memoria/{memory_id}")
def memoria_delete(memory_id: int) -> Dict[str, str]:
    delete_memory(conn, memory_id)
    return {"status": "deleted"}


@app.get("/memoria/synthesis")
def memoria_synthesis(window: str = "daily") -> Dict[str, Any]:
    now = datetime.utcnow()
    since = (now - timedelta(days=1 if window == "daily" else 7)).isoformat()
    cipher = get_cipher(os.getenv("MEMORIA_ENCRYPT_AT_REST", "0") == "1")
    memories = query_memories(conn, since=since, limit=500, cipher=cipher)
    by_app: Dict[str, int] = {}
    tags: Dict[str, int] = {}
    for m in memories:
        by_app[m["app_name"]] = by_app.get(m["app_name"], 0) + 1
        for t in m["tags"]:
            tags[t] = tags.get(t, 0) + 1
    summary = {
        "window": window,
        "total_memories": len(memories),
        "top_apps": sorted(by_app.items(), key=lambda x: x[1], reverse=True)[:3],
        "top_tags": sorted(tags.items(), key=lambda x: x[1], reverse=True)[:5],
    }
    return {"summary": summary}


@app.get("/permissions")
def permissions_list() -> Dict[str, Any]:
    return {"items": get_permissions(conn)}


@app.post("/permissions/{app_name}")
def permissions_set(app_name: str, can_read: bool = True, can_write: bool = True) -> Dict[str, str]:
    set_permission(conn, app_name, can_read=can_read, can_write=can_write)
    return {"status": "updated", "app_name": app_name}
