"""Bounded, ephemeral lexical retrieval from the authoritative SQL store.

No vector database, embeddings, model calls, persistence or action authority.
Caller must authenticate and hold a serialized native read transaction.
"""
from fractions import Fraction
import re

from db.keyring import Keyring, REDACTED
from backend.access import APP, permitted

MAX_ROWS = 256
MAX_ROW_BYTES = 65536
MAX_TOTAL_BYTES = 2 * 1024 * 1024
MAX_QUERY_CHARS = 512
MAX_TERMS = 64
MAX_RESULTS = 20


class RecallBudgetError(ValueError):
    pass


def terms(text):
    return set(re.findall(r"[^\W_]+", text.casefold(), flags=re.UNICODE))


def recall(conn, principal, text, *, limit=5):
    """Rank readable records using exact Jaccard overlap; return IDs only.

    This function returns no payload, metadata, embedding or query echo.
    No matching term means abstention. The caller supplies its current
    keyring separately through recall_with_cipher.
    """
    return recall_with_cipher(conn, principal, text, limit=limit)


def recall_with_cipher(conn, principal, text, *, limit=5, cipher=None):
    if type(principal) is not str or not APP.fullmatch(principal):
        raise PermissionError("explicit application scope required")
    if not conn.in_transaction or not permitted(conn, principal, "read"):
        raise PermissionError("authorized read transaction required")
    if type(text) is not str or not 1 <= len(text) <= MAX_QUERY_CHARS:
        raise ValueError("invalid recall query length")
    query = terms(text)
    if not 1 <= len(query) <= MAX_TERMS:
        raise ValueError("invalid recall query terms")
    if type(limit) is not int or not 1 <= limit <= MAX_RESULTS:
        raise ValueError("invalid recall result limit")
    # Preflight only scoped lengths, so an oversized SQL value is not
    # materialized by the Python retrieval path. Same locked transaction.
    inventory = conn.execute(
        "SELECT id,length(CAST(content AS BLOB)) FROM memories "
        "WHERE app_name=? ORDER BY id LIMIT ?", (principal, MAX_ROWS+1)
    ).fetchall()
    if len(inventory) > MAX_ROWS:
        raise RecallBudgetError("recall row budget exceeded")
    if any(type(row[1]) is not int or row[1] > MAX_ROW_BYTES for row in inventory):
        raise RecallBudgetError("recall record budget exceeded")
    if sum(row[1] for row in inventory) > MAX_TOTAL_BYTES:
        raise RecallBudgetError("recall total byte budget exceeded")
    ranked = []
    for mid, content, encrypted in conn.execute(
        "SELECT id,content,encrypted FROM memories WHERE app_name=? ORDER BY id",
        (principal,)
    ):
        if type(content) is not str:
            continue
        if encrypted == 1:
            if not isinstance(cipher, Keyring):
                continue
            content = cipher.open(content, principal)
            if content == REDACTED:
                continue
        elif encrypted != 0:
            continue
        words = terms(content)
        overlap = len(query & words)
        if overlap:
            score = Fraction(overlap, len(query | words))
            ranked.append((score, mid))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return {"method": "ephemeral-lexical-jaccard/v1",
            "items": [{"id": mid, "score": {"numerator": score.numerator,
                                          "denominator": score.denominator}}
                      for score, mid in ranked[:limit]],
            "authority": "NONE"}
