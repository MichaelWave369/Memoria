"""Drop-in helper hooks for Triad apps to integrate with Memoria."""

from typing import Any, Dict, List
from urllib.parse import urlsplit

import requests


class MemoriaClient:
    def __init__(self, base_url: str = "http://localhost:8765", *, token: str | None = None):
        self.base_url = base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {token}"} if token is not None else {}
        if token is not None:
            target = urlsplit(self.base_url)
            if (target.scheme != "http" or target.hostname not in ("localhost", "127.0.0.1", "::1")
                    or target.username or target.password or target.path or target.query or target.fragment):
                raise ValueError("Bearer credentials require a local Memoria endpoint")

    def _request(self, method, path, **kwargs):
        with requests.Session() as session:
            session.trust_env = False
            response = session.request(method, self.base_url + path, headers=self._headers,
                                       timeout=8, allow_redirects=False, **kwargs)
            if 300 <= response.status_code < 400:
                raise requests.HTTPError("Memoria redirect refused", response=response)
            return response.json()

    def store(self, content: str, app_name: str, agent_id: str, tags: List[str] | None = None, importance_score: float = 0.6, metadata: Dict[str, Any] | None = None) -> Dict[str, Any]:
        payload = {
            "content": content,
            "app_name": app_name,
            "agent_id": agent_id,
            "tags": tags or [],
            "importance_score": importance_score,
            "metadata": metadata or {},
        }
        return self._request("POST", "/memoria/store", json=payload)

    def query(self, app_name: str | None = None, agent_id: str | None = None, tag: str | None = None, limit: int = 20) -> Dict[str, Any]:
        params = {"app_name": app_name, "agent_id": agent_id, "tag": tag, "limit": limit}
        params = {k: v for k, v in params.items() if v is not None}
        return self._request("GET", "/memoria/query", params=params)

    def semantic(self, text: str, limit: int = 5) -> Dict[str, Any]:
        return self._request("POST", "/memoria/semantic", json={"text": text, "limit": limit})
