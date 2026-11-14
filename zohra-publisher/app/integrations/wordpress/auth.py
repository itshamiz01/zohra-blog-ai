"""
Zohra — Credential Abstraction & Secret Isolation (Part 7).

Ensures WordPress write passwords and API credentials:
- Are never stored in plaintext database columns.
- Are accessed exclusively through environment secrets or credential references.
- Are strictly redacted from logs, exceptions, and API responses.
- Are inaccessible to Scout, Researcher, Writer, and Auditor layers.
"""

from __future__ import annotations

import base64
import os
import re
from dataclasses import dataclass
from typing import Any

from app.core.config import get_settings


@dataclass(frozen=True)
class WordPressCredentials:
    base_url: str
    api_url: str
    username: str
    app_password: str

    @property
    def basic_auth_header(self) -> str:
        token = f"{self.username}:{self.app_password}"
        encoded = base64.b64encode(token.encode("utf-8")).decode("utf-8")
        return f"Basic {encoded}"


class CredentialVault:
    """
    Secure retrieval for WordPress publishing credentials.
    """

    @classmethod
    def get_credentials_for_site(
        cls,
        site_id: str,
        credential_ref: str | None = None,
        base_url_override: str | None = None,
        api_url_override: str | None = None,
    ) -> WordPressCredentials | None:
        """
        Retrieves credentials from environment or secure credential mapping.
        Falls back to global settings if credential_ref is not specified.
        """
        settings = get_settings()

        # Check if environment specifies site-specific credential
        # E.g. WP_APP_PASSWORD_SITE_<site_id> or WP_APP_PASSWORD_<credential_ref>
        ref = credential_ref or site_id.replace("-", "_")
        env_user_key = f"WP_USERNAME_{ref.upper()}"
        env_pass_key = f"WP_PASSWORD_{ref.upper()}"

        username = os.getenv(env_user_key) or settings.WORDPRESS_USERNAME
        password = os.getenv(env_pass_key) or settings.WORDPRESS_APP_PASSWORD
        base_url = base_url_override or settings.WORDPRESS_URL

        if not base_url or not username or not password:
            return None

        # Build canonical api_url if not provided
        clean_base = base_url.rstrip("/")
        api_url = api_url_override or f"{clean_base}/wp-json/wp/v2"

        return WordPressCredentials(
            base_url=clean_base,
            api_url=api_url.rstrip("/"),
            username=username,
            app_password=password,
        )


# ── Secret Redaction Utilities ───────────────────────────────────────

REDACTED = "[REDACTED]"

SENSITIVE_PATTERNS = [
    re.compile(r"Basic\s+[A-Za-z0-9+/=]+", re.IGNORECASE),
    re.compile(r"Bearer\s+[A-Za-z0-9\-_.]+", re.IGNORECASE),
    re.compile(r"(password|secret|app_password|access_token|key)[\"':=\s]+([^\s,;\"'}{]+)", re.IGNORECASE),
]


def redact_secrets(text: str) -> str:
    """Redacts authorization headers, application passwords, and secret tokens from strings."""
    if not text:
        return text
    redacted = re.sub(r"Basic\s+[A-Za-z0-9+/=]+", f"Basic {REDACTED}", text, flags=re.IGNORECASE)
    redacted = re.sub(r"Bearer\s+[A-Za-z0-9\-_.]+", f"Bearer {REDACTED}", redacted, flags=re.IGNORECASE)
    redacted = re.sub(
        r"(password|secret|app_password|access_token|token|key)([\"':=\s]+)([^\s,;\"'}{]+)",
        rf"\1\2{REDACTED}",
        redacted,
        flags=re.IGNORECASE,
    )
    return redacted




def sanitize_dict_for_logging(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively replaces sensitive dictionary keys with [REDACTED]."""
    safe: dict[str, Any] = {}
    sensitive_keys = {"password", "app_password", "secret", "token", "authorization", "auth"}
    for k, v in data.items():
        if any(sens in k.lower() for sens in sensitive_keys):
            safe[k] = REDACTED
        elif isinstance(v, dict):
            safe[k] = sanitize_dict_for_logging(v)
        elif isinstance(v, list):
            safe[k] = [
                sanitize_dict_for_logging(item) if isinstance(item, dict) else item
                for item in v
            ]
        else:
            safe[k] = v
    return safe
