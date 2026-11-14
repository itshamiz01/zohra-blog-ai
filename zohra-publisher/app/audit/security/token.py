"""
Zohra — Audit Token & Cryptographic Fingerprinting (Part 6).

Implements Section 198 & 199 Content Hash Protection:
- Audit Token: Signed cryptographic string binding (draft_hash, audit_id, audit_fingerprint, decision, timestamp).
- Audit Fingerprint: Reproducible hash of (content_hash, research_package_version, policy_version, auditor_version).
- Post-Audit Mutation Guard: Detects if any post-approval modification occurred to the approved draft.
  Part 7 refuses publication preparation unless current_content_hash == audited_content_hash.
"""

from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime

from app.core.config import get_settings


class AuditTokenManager:
    """Generates and validates signed approval tokens and content hash fingerprints."""

    @staticmethod
    def generate_audit_fingerprint(
        content_hash: str,
        research_package_version: int,
        policy_version: str = "policy-v1.0",
        auditor_version: str = "part6-v1.0",
    ) -> str:
        """Deterministic fingerprint of draft content, research version, and auditor policies."""
        combined = f"{content_hash}||{research_package_version}||{policy_version}||{auditor_version}"
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()

    @staticmethod
    def sign_audit_token(
        audit_id: str,
        content_hash: str,
        audit_fingerprint: str,
        decision: str,
        timestamp: datetime | None = None,
    ) -> str:
        """Generates an HMAC-SHA256 signed audit token that Part 7 validates before publication."""
        ts_str = (timestamp or datetime.now(UTC)).isoformat()
        payload = f"{audit_id}|{content_hash}|{audit_fingerprint}|{decision}|{ts_str}"

        settings = get_settings()
        secret_key_str = getattr(settings, "SECRET_KEY", "default-zohra-audit-secret-key-32b")
        secret_key = secret_key_str.encode("utf-8")
        signature = hmac.new(secret_key, payload.encode("utf-8"), hashlib.sha256).hexdigest()

        return f"zohra-audit-v1.{payload}.{signature}"

    @staticmethod
    def verify_audit_token(
        token: str,
        current_content_hash: str,
    ) -> tuple[bool, str]:
        """Validates token authenticity and verifies that content has NOT been mutated post-audit."""
        try:
            if not token.startswith("zohra-audit-v1."):
                return False, "Malformed audit token format"

            remainder = token[len("zohra-audit-v1.") :]
            # signature is the last component separated by dot
            parts = remainder.rsplit(".", 1)
            if len(parts) != 2:
                return False, "Malformed audit token format"

            payload, signature = parts[0], parts[1]
            settings = get_settings()
            secret_key_str = getattr(settings, "SECRET_KEY", "default-zohra-audit-secret-key-32b")
            secret_key = secret_key_str.encode("utf-8")
            expected_sig = hmac.new(secret_key, payload.encode("utf-8"), hashlib.sha256).hexdigest()

            if not hmac.compare_digest(signature, expected_sig):
                return False, "Invalid audit token cryptographic signature"

            elements = payload.split("|")
            if len(elements) < 5:
                return False, "Invalid payload structure"

            token_content_hash = elements[1]
            token_decision = elements[3]

            if token_decision != "PASS":
                return False, f"Audit token indicates non-PASS decision: {token_decision}"

            # Post-audit mutation check
            if token_content_hash != current_content_hash:
                return False, f"CONTENT HASH MISMATCH: Audited content ({token_content_hash[:12]}...) != Current content ({current_content_hash[:12]}...). Re-audit required."

            return True, "Valid and unmodified"
        except Exception as e:
            return False, f"Token validation error: {e}"
