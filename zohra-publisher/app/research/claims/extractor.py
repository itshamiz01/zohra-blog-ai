"""
Zohra — Atomic Claim Extractor.

Decomposes complex sentences into discrete atomic claims, classifying claim types,
importance, time sensitivity, and attribution requirements.
"""

from __future__ import annotations

import re
from typing import Any

from app.discovery.security.firewall import INJECTION_PATTERNS
from app.research.claims.canonicalizer import ClaimCanonicalizer
from app.schemas.research import ClaimImportance, ClaimType


class ExtractedClaimItem:
    def __init__(
        self,
        claim_text: str,
        normalized_claim: str,
        claim_type: ClaimType,
        importance: ClaimImportance,
        subject: str | None = None,
        predicate: str | None = None,
        object_value: str | None = None,
        numeric_value: float | None = None,
        unit: str | None = None,
        currency: str | None = None,
        region: str | None = None,
        temporal_scope: str | None = None,
        time_sensitive: bool = False,
        attribution_required: bool = False,
        evidence_excerpt: str | None = None,
    ):
        self.claim_text = claim_text
        self.normalized_claim = normalized_claim
        self.claim_type = claim_type
        self.importance = importance
        self.subject = subject
        self.predicate = predicate
        self.object_value = object_value
        self.numeric_value = numeric_value
        self.unit = unit
        self.currency = currency
        self.region = region
        self.temporal_scope = temporal_scope
        self.time_sensitive = time_sensitive
        self.attribution_required = attribution_required
        self.evidence_excerpt = evidence_excerpt

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_text": self.claim_text,
            "normalized_claim": self.normalized_claim,
            "claim_type": self.claim_type.value,
            "importance": self.importance.value,
            "subject": self.subject,
            "predicate": self.predicate,
            "object_value": self.object_value,
            "numeric_value": self.numeric_value,
            "unit": self.unit,
            "currency": self.currency,
            "region": self.region,
            "temporal_scope": self.temporal_scope,
            "time_sensitive": self.time_sensitive,
            "attribution_required": self.attribution_required,
            "evidence_excerpt": self.evidence_excerpt,
        }


class AtomicClaimExtractor:
    """Extracts atomic factual claims from document passages."""

    ATTRIBUTION_MARKERS = [
        re.compile(r"\b(?:claims?|stated?|announced?|according to|said)\b", re.I),
        re.compile(r'["“][^"”]+["”]'),
    ]

    CONJUNCTION_SPLITTERS = re.compile(
        r"(?:,\s*(?:and\s+)?(?=costs?|supports?|requires?|features?|launche?d?)|,\s*and\s+|\s+and\s+(?=costs?|supports?|requires?|features?|launche?d?)|;\s*|\.\s+)",
        re.I,
    )


    @classmethod
    def decompose_sentence(cls, sentence: str) -> list[str]:
        """Breaks compound sentences with multiple factual propositions into atomic clauses."""
        s = sentence.strip()
        if not s:
            return []

        # Check for multiple propositions joined by conjunctions
        parts = cls.CONJUNCTION_SPLITTERS.split(s)
        clean_parts = []
        for p in parts:
            p_strip = p.strip().rstrip(".,;")
            if len(p_strip.split()) >= 2:
                clean_parts.append(p_strip)

        return clean_parts or [s]

    @classmethod
    def extract_claims_from_text(
        cls,
        text: str,
        context_entity: str | None = None,
        context_region: str | None = None,
    ) -> list[ExtractedClaimItem]:
        """Extracts atomic claims from a block of text."""
        # Split into sentences
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        claims: list[ExtractedClaimItem] = []
        seen_signatures: set[str] = set()

        for sent in sentences:
            if len(sent.split()) < 2 or len(sent) > 500:
                continue

            # Strip prompt injection instructions from candidate sentences
            if any(pat.search(sent) for pat in INJECTION_PATTERNS):
                continue

            clauses = cls.decompose_sentence(sent)
            for clause in clauses:
                if any(pat.search(clause) for pat in INJECTION_PATTERNS):
                    continue
                canon = ClaimCanonicalizer.canonicalize(clause, context_region=context_region)
                sig = canon.canonical_signature()
                if sig in seen_signatures:
                    continue
                seen_signatures.add(sig)

                # Determine claim type
                clause_lower = clause.lower()
                c_type = ClaimType.FACT
                time_sensitive = False
                importance = ClaimImportance.MAJOR

                if canon.currency or any(w in clause_lower for w in ("cost", "price", "pricing", "fee", "free plan")):
                    c_type = ClaimType.PRICE
                    time_sensitive = True
                    importance = ClaimImportance.CRITICAL
                elif canon.numeric_value is not None and any(w in clause_lower for w in ("limit", "quota", "max")):
                    c_type = ClaimType.LIMITATION
                    time_sensitive = True
                    importance = ClaimImportance.HIGH
                elif canon.numeric_value is not None:
                    c_type = ClaimType.NUMBER
                    importance = ClaimImportance.MAJOR
                elif canon.effective_date or any(w in clause_lower for w in ("launch", "release", "announced")):
                    c_type = ClaimType.DATE
                    time_sensitive = True
                    importance = ClaimImportance.CRITICAL
                elif any(w in clause_lower for w in ("support", "feature", "workflow", "capable", "generate")):
                    c_type = ClaimType.CAPABILITY
                    time_sensitive = True
                    importance = ClaimImportance.MAJOR
                elif any(w in clause_lower for w in ("vs", "compare", "faster than", "better than")):
                    c_type = ClaimType.COMPARISON
                    importance = ClaimImportance.MAJOR

                # Check attribution requirements
                attribution_required = False
                for att_pat in cls.ATTRIBUTION_MARKERS:
                    if att_pat.search(clause):
                        attribution_required = True
                        break

                # Normalized claim text (clean spaces, lower)
                norm_claim = " ".join(clause.lower().split())

                claims.append(
                    ExtractedClaimItem(
                        claim_text=clause,
                        normalized_claim=norm_claim,
                        claim_type=c_type,
                        importance=importance,
                        subject=canon.subject or context_entity,
                        predicate=canon.predicate,
                        object_value=canon.object_value,
                        numeric_value=canon.numeric_value,
                        unit=canon.unit,
                        currency=canon.currency,
                        region=canon.region,
                        temporal_scope=canon.temporal_scope,
                        time_sensitive=time_sensitive,
                        attribution_required=attribution_required,
                        evidence_excerpt=clause,
                    )
                )

        return claims
