"""Deterministic, conservative candidate identity helpers."""

import hashlib
import re
from urllib.parse import urlsplit, urlunsplit


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold()).strip()


def canonicalize_url(value: str | None) -> str | None:
    if not value:
        return None
    parts = urlsplit(value)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        return None
    return urlunsplit(
        (parts.scheme.lower(), parts.hostname.lower(), parts.path.rstrip("/"), "", "")
    )


def fallback_fingerprint(
    provider: str, entity_type: str, name: str, full_address: str
) -> str | None:
    values = [normalize_text(value) for value in (provider, entity_type, name, full_address)]
    if not all(values):
        return None
    return hashlib.sha256("\x1f".join(values).encode()).hexdigest()


def match_band(score: float, *, protected: bool, exact_provider_identity: bool) -> str:
    if exact_provider_identity:
        return "auto_link"
    if protected:
        return "review" if score >= 0.85 else "separate"
    if score >= 0.98:
        return "auto_link"
    if score >= 0.85:
        return "review"
    return "separate"
