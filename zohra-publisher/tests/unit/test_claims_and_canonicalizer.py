"""
Unit tests for Atomic Claim Extraction and Canonicalization.
"""

from __future__ import annotations

from app.research.claims.canonicalizer import ClaimCanonicalizer
from app.research.claims.extractor import AtomicClaimExtractor
from app.schemas.research import ClaimType


def test_atomic_claim_decomposition_of_compound_sentence():
    compound_sentence = (
        "Model X launched in India in September, costs ₹1,999 and supports 4K video."
    )
    clauses = AtomicClaimExtractor.decompose_sentence(compound_sentence)
    assert len(clauses) >= 3

    claims = AtomicClaimExtractor.extract_claims_from_text(
        compound_sentence, context_entity="Model X", context_region="India"
    )
    assert len(claims) >= 3

    # Check pricing claim
    price_claim = next((c for c in claims if c.claim_type == ClaimType.PRICE), None)
    assert price_claim is not None
    assert price_claim.numeric_value == 1999.0
    assert price_claim.currency == "INR"
    assert price_claim.region == "India"
    assert price_claim.time_sensitive is True


def test_canonicalizer_usd_and_numeric_units():
    data = ClaimCanonicalizer.canonicalize("The Pro plan costs $29.99 per month with 100 generations.")
    assert data.numeric_value == 29.99
    assert data.currency == "USD"

    unit_data = ClaimCanonicalizer.canonicalize("Export file size limit is 10 GB per video.")
    assert unit_data.numeric_value == 10.0
    assert unit_data.unit == "GB"


def test_canonicalizer_preserves_distinct_scopes_in_signatures():
    data_us = ClaimCanonicalizer.canonicalize("Model X costs $20/month", context_region="US")
    data_in = ClaimCanonicalizer.canonicalize("Model X costs ₹1,999/month", context_region="India")

    assert data_us.canonical_signature() != data_in.canonical_signature()


def test_attribution_required_for_unverified_company_claims():
    text = 'Company spokesperson stated that "Model X renders twice as fast as competing engines".'
    claims = AtomicClaimExtractor.extract_claims_from_text(text, context_entity="Model X")
    assert len(claims) >= 1
    assert claims[0].attribution_required is True
