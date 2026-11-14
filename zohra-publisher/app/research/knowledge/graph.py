"""
Zohra — Knowledge Graph Builder.

Builds structured entity relationships (created_by, owned_by, competes_with, available_in,
released_by, uses, integrates_with) with evidence anchors and confidence scores.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any


class EntityRelationEdge:
    def __init__(
        self,
        subject: str,
        predicate: str,
        object_value: str,
        confidence_score: float = 85.0,
        evidence_text: str | None = None,
        source_id: str | None = None,
    ):
        self.subject = subject
        self.predicate = predicate
        self.object_value = object_value
        self.confidence_score = confidence_score
        self.evidence_text = evidence_text
        self.source_id = source_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject": self.subject,
            "predicate": self.predicate,
            "object_value": self.object_value,
            "confidence_score": self.confidence_score,
            "evidence_text": self.evidence_text,
            "source_id": self.source_id,
        }


class KnowledgeGraphBuilder:
    """Extracts factual relationships between primary entities and related concepts."""

    RELATION_PATTERNS = [
        ("created_by", re.compile(r"\b([A-Za-z0-9\s]+)\s+(?:was\s+created\s+by|developed\s+by|built\s+by|from)\s+([A-Za-z0-9\s]+)", re.I)),
        ("released_by", re.compile(r"\b([A-Za-z0-9\s]+)\s+(?:was\s+released\s+by|launched\s+by|announced\s+by)\s+([A-Za-z0-9\s]+)", re.I)),
        ("competes_with", re.compile(r"\b([A-Za-z0-9\s]+)\s+(?:competes\s+with|vs\.?|alternative\s+to|rivals?)\s+([A-Za-z0-9\s]+)", re.I)),
        ("integrates_with", re.compile(r"\b([A-Za-z0-9\s]+)\s+(?:integrates\s+with|supports|connects\s+to)\s+([A-Za-z0-9\s]+)", re.I)),
        ("available_in", re.compile(r"\b([A-Za-z0-9\s]+)\s+(?:is\s+available\s+in|rolled\s+out\s+in|launched\s+in)\s+([A-Za-z0-9\s]+)", re.I)),
    ]

    @classmethod
    def extract_relationships(
        cls,
        claims: Sequence[dict[str, Any]],
        known_entities: Sequence[str] | None = None,
    ) -> list[EntityRelationEdge]:
        edges: list[EntityRelationEdge] = []
        seen_edges: set[tuple[str, str, str]] = set()

        for c in claims:
            text = c.get("claim_text", "")
            src_id = c.get("source_id")
            conf = float(c.get("confidence_score", 85.0))

            for pred_name, pat in cls.RELATION_PATTERNS:
                m = pat.search(text)
                if m:
                    subj = m.group(1).strip()
                    obj = m.group(2).strip()

                    # Clean up trailing words
                    subj = " ".join(subj.split()[:4])
                    obj = " ".join(obj.split()[:4])

                    edge_key = (subj.lower(), pred_name, obj.lower())
                    if edge_key not in seen_edges and len(subj) > 2 and len(obj) > 2:
                        seen_edges.add(edge_key)
                        edges.append(
                            EntityRelationEdge(
                                subject=subj,
                                predicate=pred_name,
                                object_value=obj,
                                confidence_score=conf,
                                evidence_text=text,
                                source_id=src_id,
                            )
                        )

        return edges
