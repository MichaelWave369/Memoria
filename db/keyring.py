"""Versioned Fernet text envelopes with explicit operator-provisioned keys.

No password derivation, default key, legacy decrypt or automatic migration.
The keyring is process-local configuration, not an independent key vault.
"""
import base64
import json
import os
import re

from cryptography.fernet import Fernet, InvalidToken

KEY_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")
KEY = re.compile(r"[A-Za-z0-9_-]{43}=")
PREFIX = "memoria:v1:"
REDACTED = "[Encrypted memory: key unavailable or record not verified]"


class KeyConfigurationError(ValueError):
    pass


def _unique(pairs):
    out = {}
    for name, value in pairs:
        if name in out:
            raise KeyConfigurationError("duplicate encryption key ID")
        out[name] = value
    return out


class Keyring:
    def __init__(self, keys, active):
        if (type(keys) is not dict or not 1 <= len(keys) <= 32
                or type(active) is not str or active not in keys):
            raise KeyConfigurationError("invalid encryption keyring")
        decoded = {}
        for name, value in keys.items():
            if (type(name) is not str or not KEY_ID.fullmatch(name)
                    or type(value) is not str or not KEY.fullmatch(value)):
                raise KeyConfigurationError("invalid encryption keyring")
            raw = base64.urlsafe_b64decode(value)
            if len(raw) != 32 or base64.urlsafe_b64encode(raw).decode("ascii") != value:
                raise KeyConfigurationError("invalid encryption key encoding")
            decoded[name] = raw
        if len(set(decoded.values())) != len(decoded):
            raise KeyConfigurationError("duplicate encryption key material")
        self.active = active
        self._keys = {name: Fernet(base64.urlsafe_b64encode(raw))
                      for name, raw in decoded.items()}

    def seal(self, content, app):
        # Bind the application and key ID inside the authenticated token.
        # No row identity binding or metadata encryption is claimed.
        body = json.dumps({"schema": "memoria.text/v1", "key_id": self.active,
                           "app": app, "content": content},
                          ensure_ascii=True, separators=(",", ":"), sort_keys=True)
        token = self._keys[self.active].encrypt(body.encode("ascii")).decode("ascii")
        return PREFIX + self.active + ":" + token

    def open(self, envelope, app):
        if type(envelope) is not str or not envelope.startswith(PREFIX):
            return REDACTED
        try:
            name, token = envelope[len(PREFIX):].split(":", 1)
            if not KEY_ID.fullmatch(name) or name not in self._keys:
                return REDACTED
            body = json.loads(self._keys[name].decrypt(token.encode("ascii")))
            if (type(body) is not dict or set(body) != {"schema", "key_id", "app", "content"}
                    or body["schema"] != "memoria.text/v1" or body["key_id"] != name
                    or body["app"] != app or type(body["content"]) is not str):
                return REDACTED
            return body["content"]
        except (InvalidToken, ValueError, UnicodeError, RecursionError):
            return REDACTED


def load_keyring():
    raw = os.getenv("MEMORIA_ENCRYPTION_KEYS", "")
    active = os.getenv("MEMORIA_ACTIVE_KEY_ID", "")
    if not raw or len(raw) > 8192:
        raise KeyConfigurationError("explicit encryption keyring required")
    try:
        keys = json.loads(raw, object_pairs_hook=_unique)
    except (ValueError, RecursionError):
        raise KeyConfigurationError("invalid encryption keyring") from None
    return Keyring(keys, active)


def configured_cipher():
    mode = os.getenv("MEMORIA_ENCRYPT_AT_REST", "0")
    if mode not in ("0", "1"):
        raise KeyConfigurationError("invalid encryption mode")
    return load_keyring() if mode == "1" else None
