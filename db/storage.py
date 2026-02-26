import base64
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from cryptography.fernet import Fernet

DB_PATH = Path(os.getenv("MEMORIA_DB_PATH", "memoria.db"))


def _default_key() -> bytes:
    seed = os.getenv("MEMORIA_KEY", "memoria-local-key-seed")
    return base64.urlsafe_b64encode(seed.encode().ljust(32, b"0")[:32])


def get_cipher(enabled: bool) -> Optional[Fernet]:
    if not enabled:
        return None
    return Fernet(_default_key())


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            app_name TEXT NOT NULL,
            agent_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            tags TEXT NOT NULL,
            importance_score REAL NOT NULL,
            metadata_json TEXT NOT NULL,
            encrypted INTEGER DEFAULT 0
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS app_permissions (
            app_name TEXT PRIMARY KEY,
            can_read INTEGER DEFAULT 1,
            can_write INTEGER DEFAULT 1
        )
        """
    )
    conn.commit()


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    return conn


def encrypt_if_needed(content: str, cipher: Optional[Fernet]) -> tuple[str, int]:
    if not cipher:
        return content, 0
    return cipher.encrypt(content.encode()).decode(), 1


def decrypt_if_needed(content: str, encrypted: int, cipher: Optional[Fernet]) -> str:
    if not encrypted:
        return content
    if not cipher:
        return "[Encrypted memory: enable encryption key to decrypt]"
    return cipher.decrypt(content.encode()).decode()


def store_memory(
    conn: sqlite3.Connection,
    memory: Dict[str, Any],
    cipher: Optional[Fernet] = None,
) -> int:
    tags = json.dumps(memory.get("tags", []))
    metadata_json = json.dumps(memory.get("metadata", {}))
    timestamp = memory.get("timestamp") or datetime.utcnow().isoformat()
    content, encrypted = encrypt_if_needed(memory["content"], cipher)

    cur = conn.execute(
        """
        INSERT INTO memories (content, app_name, agent_id, timestamp, tags, importance_score, metadata_json, encrypted)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            content,
            memory["app_name"],
            memory.get("agent_id", "unknown"),
            timestamp,
            tags,
            float(memory.get("importance_score", 0.5)),
            metadata_json,
            encrypted,
        ),
    )
    conn.commit()
    return int(cur.lastrowid)


def query_memories(
    conn: sqlite3.Connection,
    app_name: Optional[str] = None,
    agent_id: Optional[str] = None,
    tag: Optional[str] = None,
    since: Optional[str] = None,
    limit: int = 100,
    cipher: Optional[Fernet] = None,
) -> List[Dict[str, Any]]:
    clauses, params = [], []
    if app_name:
        clauses.append("app_name = ?")
        params.append(app_name)
    if agent_id:
        clauses.append("agent_id = ?")
        params.append(agent_id)
    if since:
        clauses.append("timestamp >= ?")
        params.append(since)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    rows = conn.execute(
        f"SELECT * FROM memories {where} ORDER BY timestamp DESC LIMIT ?", (*params, limit)
    ).fetchall()

    out: List[Dict[str, Any]] = []
    for row in rows:
        tags = json.loads(row["tags"])
        if tag and tag not in tags:
            continue
        out.append(
            {
                "id": row["id"],
                "content": decrypt_if_needed(row["content"], row["encrypted"], cipher),
                "app_name": row["app_name"],
                "agent_id": row["agent_id"],
                "timestamp": row["timestamp"],
                "tags": tags,
                "importance_score": row["importance_score"],
                "metadata": json.loads(row["metadata_json"]),
                "encrypted": row["encrypted"],
            }
        )
    return out


def delete_memory(conn: sqlite3.Connection, memory_id: int) -> None:
    conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
    conn.commit()


def set_permission(conn: sqlite3.Connection, app_name: str, can_read: bool, can_write: bool) -> None:
    conn.execute(
        """
        INSERT INTO app_permissions(app_name, can_read, can_write)
        VALUES (?, ?, ?)
        ON CONFLICT(app_name) DO UPDATE SET can_read=excluded.can_read, can_write=excluded.can_write
        """,
        (app_name, int(can_read), int(can_write)),
    )
    conn.commit()


def get_permissions(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    rows = conn.execute("SELECT * FROM app_permissions ORDER BY app_name").fetchall()
    return [dict(row) for row in rows]
