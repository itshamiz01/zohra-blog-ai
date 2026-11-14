"""
Zohra — Source Independence & Syndication Engine.

Detects syndicated reporting, copied press releases, shared wire copy, and circular
citation loops to prevent 10 copied websites from being counted as 10 independent confirmations.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence


class SourceIndependenceEngine:
    """Groups sources that share wire copy or press releases into independence groups."""

    ATTRIBUTION_PATTERNS = [
        re.compile(r"(?:according to|reported by|via|citing|source:)\s+([A-Za-z0-9\s\.\-]{3,40})", re.I),
        re.compile(r"(?:press release|prnewswire|businesswire|globe\s?newswire|pr\s?web)", re.I),
    ]

    @classmethod
    def extract_text_fingerprint(cls, text: str) -> set[str]:
        """Extracts 4-gram shingles for similarity matching."""
        words = re.findall(r"\b[a-z0-9]+\b", text.lower())
        if len(words) < 4:
            return set(words)
        return {" ".join(words[i : i + 4]) for i in range(len(words) - 3)}

    @classmethod
    def compute_jaccard_similarity(cls, set_a: set[str], set_b: set[str]) -> float:
        if not set_a or not set_b:
            return 0.0
        intersection = len(set_a.intersection(set_b))
        union = len(set_a.union(set_b))
        return intersection / union if union > 0 else 0.0

    @classmethod
    def detect_independence_groups(
        cls,
        sources: Sequence[dict],
    ) -> dict[str, str]:
        """
        Takes a list of source dicts (with 'id', 'url', 'publisher', 'title', 'text', 'metadata')
        and assigns each an independence_group_id.

        Returns:
            dict mapping source_id -> independence_group_id
        """
        assignments: dict[str, str] = {}
        fingerprints: dict[str, set[str]] = {}

        # 1. First pass: group by explicit publisher / PR wires or PR attribution
        for s in sources:
            s_id = str(s["id"])
            text = s.get("text") or s.get("content_text") or ""
            publisher = (s.get("publisher") or "").lower().strip()
            url = s.get("url") or ""

            # Check PR wire indicators
            is_wire = False
            for pat in cls.ATTRIBUTION_PATTERNS:
                if pat.search(text) or pat.search(url) or pat.search(publisher):
                    is_wire = True
                    break

            if is_wire and ("prnewswire" in url.lower() or "businesswire" in url.lower()):
                # Standardize wire group
                assignments[s_id] = "wire_group_pr_release"
                continue

            fingerprints[s_id] = cls.extract_text_fingerprint(text)

        # 2. Second pass: Pairwise content similarity for near-duplicate/syndicated copy
        unassigned_ids = [str(s["id"]) for s in sources if str(s["id"]) not in assignments]

        for i, s1_id in enumerate(unassigned_ids):
            if s1_id in assignments:
                continue
            group_id = f"indep_{hashlib.md5(s1_id.encode()).hexdigest()[:12]}"
            assignments[s1_id] = group_id

            fp1 = fingerprints.get(s1_id, set())
            if not fp1:
                continue

            for s2_id in unassigned_ids[i + 1 :]:
                if s2_id in assignments:
                    continue
                fp2 = fingerprints.get(s2_id, set())
                # If shingle similarity > 0.45, it is syndicated/copied reporting
                sim = cls.compute_jaccard_similarity(fp1, fp2)
                if sim >= 0.45:
                    assignments[s2_id] = group_id

        # Ensure all sources have an assignment
        for s in sources:
            s_id = str(s["id"])
            if s_id not in assignments:
                assignments[s_id] = f"indep_{hashlib.md5(s_id.encode()).hexdigest()[:12]}"

        return assignments

    @classmethod
    def detect_circular_citations(
        cls,
        citations: list[tuple[str, str]],  # (source_id_from, source_id_to)
    ) -> set[tuple[str, str]]:
        """
        Detects circular citation loops (e.g., A -> B, B -> C, C -> A).
        Returns set of edge tuples involved in loops.
        """
        adj: dict[str, set[str]] = {}
        for src, dst in citations:
            adj.setdefault(src, set()).add(dst)

        loops: set[tuple[str, str]] = set()

        def dfs(node: str, visited: set[str], path: list[str]):
            visited.add(node)
            path.append(node)
            for neighbor in adj.get(node, []):
                if neighbor in path:
                    idx = path.index(neighbor)
                    cycle = path[idx:]
                    for k in range(len(cycle) - 1):
                        loops.add((cycle[k], cycle[k + 1]))
                    loops.add((cycle[-1], neighbor))
                elif neighbor not in visited:
                    dfs(neighbor, visited, path)
            path.pop()

        visited_nodes: set[str] = set()
        for node in adj:
            if node not in visited_nodes:
                dfs(node, visited_nodes, [])

        return loops
