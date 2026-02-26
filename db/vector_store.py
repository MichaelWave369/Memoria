import hashlib
import os
from typing import Any, Dict, List

import chromadb
import requests


def _fallback_embedding(text: str, dims: int = 384) -> List[float]:
    digest = hashlib.sha256(text.encode()).digest()
    values = list(digest) * (dims // len(digest) + 1)
    return [v / 255 for v in values[:dims]]


def generate_embedding(text: str) -> List[float]:
    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
    try:
        response = requests.post(
            f"{ollama_url}/api/embeddings",
            json={"model": model, "prompt": text},
            timeout=4,
        )
        response.raise_for_status()
        return response.json().get("embedding") or _fallback_embedding(text)
    except Exception:
        return _fallback_embedding(text)


def get_collection() -> Any:
    client = chromadb.PersistentClient(path=os.getenv("MEMORIA_CHROMA_PATH", "chroma_data"))
    return client.get_or_create_collection(name="memories")


def upsert_memory(collection: Any, memory_id: int, content: str, metadata: Dict[str, Any]) -> None:
    emb = generate_embedding(content)
    collection.upsert(
        ids=[str(memory_id)],
        documents=[content],
        metadatas=[metadata],
        embeddings=[emb],
    )


def query_similar(collection: Any, query: str, limit: int = 5) -> List[Dict[str, Any]]:
    emb = generate_embedding(query)
    results = collection.query(query_embeddings=[emb], n_results=limit)
    docs = results.get("documents", [[]])[0]
    ids = results.get("ids", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    return [
        {"id": ids[i], "content": docs[i], "metadata": metas[i] if i < len(metas) else {}}
        for i in range(len(docs))
    ]
