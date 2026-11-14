"""
Zohra — Independent Claim Extractor (Part 6).

Extracts factual claims independently from the final rendered prose of an article.
Catches claims inadvertently introduced during rewriting, brand transformation,
transitions, summary writing, FAQ creation, and table generation.
Distinguishes material factual claims from non-factual editorial prose.
"""

from __future__ import annotations

import re

from app.schemas.audit import ExtractedClaim, ParsedDraftContent


class IndependentClaimExtractor:
    """Extracts material factual claims from parsed draft content."""

    # Words and patterns that signal factual statements rather than meta/connective prose
    FACTUAL_INDICATORS = [
        r"\b(?:costs?|prices?|\$|€|£|¥)\b",
        r"\b(?:percent|%|increased|decreased|revenue|growth)\b",
        r"\b(?:released|launched|announced|acquired|founded|discovered|stated)\b",
        r"\b(?:supports|features|includes|provides|contains|requires|limits)\b",
        r"\b(?:version|v\d+|\b\d{4}\b)\b",
        r"\b(?:according to|reported|confirmed|denied|claims)\b",
    ]

    # Meta/editorial connective phrases that do not make factual assertions about the external world
    NON_MATERIAL_PATTERNS = [
        r"^in this article[,\s]",
        r"^this section explains",
        r"^let['’]s dive in",
        r"^in conclusion[,\s]",
        r"^as we will see",
        r"^read on to learn",
        r"^below is a table",
        r"^the following guide covers",
    ]

    def extract_claims(self, content: ParsedDraftContent) -> list[ExtractedClaim]:
        """Extracts all material factual claims across sections, FAQs, and tables."""
        claims: list[ExtractedClaim] = []

        # 1. Extract from sections
        for sec in content.sections:
            for p in sec.paragraphs:
                for s in p.sentences:
                    claim = self._evaluate_sentence_claim(sec.section_id, s.sentence_index, s.text)
                    if claim:
                        claims.append(claim)

        # 2. Extract from FAQs
        for idx, faq in enumerate(content.faqs):
            q_text = faq.get("question", "")
            a_text = faq.get("answer", "")
            if a_text:
                faq_claim = self._evaluate_sentence_claim(
                    f"faq_{idx}",
                    0,
                    f"{q_text}: {a_text}",
                    is_faq=True,
                )
                if faq_claim:
                    claims.append(faq_claim)

        # 3. Extract from Tables
        for t_idx, table in enumerate(content.tables):
            title = table.get("title", f"Table {t_idx + 1}")
            rows = table.get("rows", [])
            headers = table.get("headers", [])
            for r_idx, row in enumerate(rows):
                if isinstance(row, dict):
                    row_desc = ", ".join([f"{k}: {v}" for k, v in row.items()])
                elif isinstance(row, list) and headers:
                    row_desc = ", ".join([f"{h}: {val}" for h, val in zip(headers, row, strict=False)])
                else:
                    row_desc = str(row)

                tbl_claim = ExtractedClaim(
                    section_id=f"table_{t_idx}",
                    sentence_index=r_idx,
                    claim_text=f"[{title}] {row_desc}",
                    normalized_claim=self._normalize_text(f"{title} {row_desc}"),
                    claim_type="table_cell",
                    importance="major",
                    numbers_found=self._extract_numbers(row_desc),
                    dates_found=self._extract_dates(row_desc),
                )
                claims.append(tbl_claim)

        return claims

    def _evaluate_sentence_claim(
        self,
        section_id: str,
        sentence_index: int,
        text: str,
        is_faq: bool = False,
    ) -> ExtractedClaim | None:
        """Determines if a sentence is a material factual claim and extracts details."""
        clean_text = text.strip()
        if len(clean_text) < 15:
            return None

        # Check for non-material prose
        lower_text = clean_text.lower()
        for nmp in self.NON_MATERIAL_PATTERNS:
            if re.search(nmp, lower_text):
                return None

        numbers = self._extract_numbers(clean_text)
        dates = self._extract_dates(clean_text)

        # Has factual indicators or numbers/dates
        is_factual = bool(numbers or dates)
        if not is_factual:
            for pattern in self.FACTUAL_INDICATORS:
                if re.search(pattern, lower_text):
                    is_factual = True
                    break

        if not is_factual and not is_faq:
            # Check length/structure for asserting statements
            words = clean_text.split()
            if len(words) < 6:
                return None
            # If purely opinion/advice ("You should check your settings"), consider non-material
            if lower_text.startswith(("make sure to", "ensure that you", "remember to", "you should")):
                return None

        # Determine importance
        importance = "supporting"
        if numbers or dates:
            importance = "major"
        if any(w in lower_text for w in ["price", "cost", "law", "treatment", "cure", "death", "founder", "ceo"]):
            importance = "critical"

        # Attribution signals in draft text
        attribution_signals = [
            r"\baccording to\b",
            r"\bclaims?\b",
            r"\balleged\b",
            r"\breported\b",
            r"\bstates?\b",
            r"\bsaid\b",
            r"\brepresentatives\b",
        ]
        has_attribution = any(re.search(pat, lower_text) for pat in attribution_signals)

        return ExtractedClaim(
            section_id=section_id,
            sentence_index=sentence_index,
            claim_text=clean_text,
            normalized_claim=self._normalize_text(clean_text),
            claim_type="faq_answer" if is_faq else "factual",
            importance=importance,
            numbers_found=numbers,
            dates_found=dates,
            requires_attribution=has_attribution,
        )

    def _normalize_text(self, text: str) -> str:
        """Normalizes claim text for deterministic token/n-gram matching."""
        # Remove citations like [src_1], punctuation, and lowercase
        cleaned = re.sub(r"\[(?:cite:)?([a-zA-Z0-9_\-]+)\]", "", text)
        cleaned = re.sub(r"[^\w\s\$\%\.]", " ", cleaned).lower()
        return " ".join(cleaned.split())

    def _extract_numbers(self, text: str) -> list[str]:
        """Extracts numeric values, prices, percentages, and metrics."""
        pattern = r"(?:\$\s*\d+(?:\.\d+)?|\b\d+(?:\.\d+)?%|\b\d+(?:,\d{3})*(?:\.\d+)?\b)"
        matches = re.findall(pattern, text)
        return [m.strip() for m in matches if m.strip() not in ["1", "2", "3"]]

    def _extract_dates(self, text: str) -> list[str]:
        """Extracts date expressions (months, years, full dates)."""
        pattern = r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:,\s*\d{4})?|\b20\d{2}\b"
        return re.findall(pattern, text, flags=re.IGNORECASE)
