"""Drop-in helper hooks for Triad apps to integrate with Memoria."""

from typing import Any, Dict, List

import requests


class MemoriaClient:
    def __init__(self, base_url: str = "http://localhost:8765"):
        self.base_url = base_url.rstrip("/")

    def store(self, content: str, app_name: str, agent_id: str, tags: List[str] | None = None, importance_score: float = 0.6, metadata: Dict[str, Any] | None = None) -> Dict[str, Any]:
        payload = {
            "content": content,
            "app_name": app_name,
            "agent_id": agent_id,
            "tags": tags or [],
            "importance_score": importance_score,
            "metadata": metadata or {},
        }
        return requests.post(f"{self.base_url}/memoria/store", json=payload, timeout=8).json()

    def query(self, app_name: str | None = None, agent_id: str | None = None, tag: str | None = None, limit: int = 20) -> Dict[str, Any]:
        params = {"app_name": app_name, "agent_id": agent_id, "tag": tag, "limit": limit}
        params = {k: v for k, v in params.items() if v is not None}
        return requests.get(f"{self.base_url}/memoria/query", params=params, timeout=8).json()

    def semantic(self, text: str, limit: int = 5) -> Dict[str, Any]:
        return requests.post(f"{self.base_url}/memoria/semantic", json={"text": text, "limit": limit}, timeout=8).json()
