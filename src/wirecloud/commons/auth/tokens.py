"""Primitives shared by browser login and optional authorization plugins."""
import base64
import hashlib
import secrets
from datetime import datetime, timezone

from wirecloud import settings


def now():
    return datetime.now(timezone.utc)


def utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def random_token() -> str:
    return secrets.token_urlsafe(32)


def pkce(verifier: str) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()


def public_base(request):
    return (getattr(settings, "AUTH_PUBLIC_URL", "") or str(request.base_url)).rstrip("/")
