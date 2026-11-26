"""Explicit application credential registry for the local Memoria API.

Operator supplies SHA-256 digests of independently generated random bearer
tokens; the request's app_name is never treated as caller authentication.
No default credentials or administrator role in this increment.
"""
import hashlib
import hmac
import json
import os
import re

APP = re.compile(r"[A-Za-z0-9._:-]{1,128}")
TOKEN = re.compile(r"[A-Za-z0-9_-]{43,128}")
DIGEST = re.compile(r"[0-9a-f]{64}")


class ConfigurationError(ValueError):
    pass


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ConfigurationError("duplicate credential registry entry")
        result[key] = value
    return result


def registry():
    raw = os.getenv("MEMORIA_API_TOKEN_SHA256", "")
    if not raw or len(raw) > 16384:
        raise ConfigurationError("credential registry missing or invalid")
    try:
        parsed = json.loads(raw, object_pairs_hook=_unique)
    except (ValueError, RecursionError):
        raise ConfigurationError("credential registry invalid") from None
    if type(parsed) is not dict or not 1 <= len(parsed) <= 64:
        raise ConfigurationError("credential registry invalid")
    if any(not APP.fullmatch(app) or type(digest) is not str
           or not DIGEST.fullmatch(digest) for app, digest in parsed.items()):
        raise ConfigurationError("credential registry invalid")
    if len(set(parsed.values())) != len(parsed):
        raise ConfigurationError("credential reuse across applications forbidden")
    return parsed


def authenticate(authorization):
    """Return the credential's exact application, or refuse."""
    rules = registry()
    if type(authorization) is not str or not authorization.startswith("Bearer "):
        raise PermissionError("application credential required")
    token = authorization[7:]
    if not TOKEN.fullmatch(token):
        raise PermissionError("application credential invalid")
    digest = hashlib.sha256(token.encode("ascii")).hexdigest()
    matches = [app for app, expected in rules.items()
               if hmac.compare_digest(digest, expected)]
    if len(matches) != 1:
        raise PermissionError("application credential invalid")
    return matches[0]


def permitted(conn, app, operation):
    """Missing and malformed native permission flags deny."""
    if operation not in ("read", "write"):
        raise ValueError("unsupported operation")
    row = conn.execute("SELECT can_read,can_write FROM app_permissions WHERE app_name=?",
                       (app,)).fetchone()
    return row is not None and row[0 if operation == "read" else 1] == 1
