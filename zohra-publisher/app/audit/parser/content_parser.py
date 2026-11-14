"""
Zohra — Content Parser (Part 6).

Parses generated editorial packages into normalized, indexed structural units:
sections, paragraphs, sentences, tables, FAQs, quotations, citations, and links.
Assigns deterministic, stable IDs (e.g., section_01, paragraph_02, sentence_03)
for precise claim verification and surgical revision routing.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from app.schemas.audit import (
    ParsedDraftContent,
    ParsedParagraph,
    ParsedSection,
    ParsedSentence,
)


class ContentParser:
    """Parses draft articles and extracts structured, indexed components."""

    @staticmethod
    def calculate_content_hash(data: dict[str, Any]) -> str:
        """Deterministically hashes core text fields of an editorial package."""
        headline = data.get("headline", "")
        slug = data.get("slug_candidate", "")
        article = data.get("article", {})
        intro = article.get("introduction", "")
        sections = article.get("sections", [])
        sections_str = json.dumps(sections, sort_keys=True)
        conclusion = article.get("conclusion", "")
        faq = article.get("faq", [])
        faq_str = json.dumps(faq, sort_keys=True)
        tables = article.get("tables", [])
        tables_str = json.dumps(tables, sort_keys=True)

        combined = f"{headline}||{slug}||{intro}||{sections_str}||{conclusion}||{faq_str}||{tables_str}"
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()

    @classmethod
    def compute_content_hash(cls, input_data: str | dict[str, Any]) -> str:
        """Computes SHA-256 hash over string text or dictionary package."""
        if isinstance(input_data, dict):
            return cls.calculate_content_hash(input_data)
        return hashlib.sha256(input_data.strip().encode("utf-8")).hexdigest()


    def parse(self, package_json: dict[str, Any]) -> ParsedDraftContent:
        """Parses an EditorialDraftPackage dictionary into structured units."""
        title = package_json.get("headline", "")
        meta_title = package_json.get("meta_title", "")
        meta_description = package_json.get("meta_description", "")
        slug = package_json.get("slug_candidate", "")
        content_hash = self.calculate_content_hash(package_json)

        article = package_json.get("article", {})
        raw_sections = article.get("sections", [])
        intro_text = article.get("introduction", "")
        conclusion_text = article.get("conclusion", "")
        faqs = article.get("faq", [])
        tables = article.get("tables", [])

        parsed_sections: list[ParsedSection] = []
        all_citations: set[str] = set()
        all_links: set[str] = set()
        all_quotes: list[dict[str, Any]] = []

        # 1. Parse Introduction as section_intro
        if intro_text:
            intro_sec = self._parse_section(
                section_id="section_intro",
                heading="Introduction",
                level=2,
                raw_text=intro_text,
                all_citations=all_citations,
                all_links=all_links,
                all_quotes=all_quotes,
            )
            parsed_sections.append(intro_sec)

        # 2. Parse Body Sections
        for idx, sec in enumerate(raw_sections, start=1):
            sec_id = sec.get("section_id") or f"section_{idx:02d}"
            heading = sec.get("heading") or f"Section {idx}"
            body = sec.get("content") or sec.get("body") or ""
            parsed_sec = self._parse_section(
                section_id=sec_id,
                heading=heading,
                level=sec.get("level", 2),
                raw_text=body,
                all_citations=all_citations,
                all_links=all_links,
                all_quotes=all_quotes,
            )
            parsed_sections.append(parsed_sec)

        # 3. Parse Conclusion as section_conclusion
        if conclusion_text:
            conc_sec = self._parse_section(
                section_id="section_conclusion",
                heading="Conclusion",
                level=2,
                raw_text=conclusion_text,
                all_citations=all_citations,
                all_links=all_links,
                all_quotes=all_quotes,
            )
            parsed_sections.append(conc_sec)

        return ParsedDraftContent(
            title=title,
            meta_title=meta_title,
            meta_description=meta_description,
            slug=slug,
            sections=parsed_sections,
            tables=tables,
            faqs=faqs,
            quotes=all_quotes,
            citations_found=sorted(all_citations),
            links_found=sorted(all_links),
            content_hash=content_hash,
        )

    def _parse_section(
        self,
        section_id: str,
        heading: str,
        level: int,
        raw_text: str,
        all_citations: set[str],
        all_links: set[str],
        all_quotes: list[dict[str, Any]],
    ) -> ParsedSection:
        """Breaks a section's text into indexed paragraphs and sentences."""
        paragraphs_raw = [p.strip() for p in re.split(r"\n\s*\n", raw_text) if p.strip()]
        parsed_paragraphs: list[ParsedParagraph] = []

        for p_idx, p_raw in enumerate(paragraphs_raw):
            sentences_raw = self._split_sentences(p_raw)
            parsed_sentences: list[ParsedSentence] = []

            for s_idx, s_raw in enumerate(sentences_raw):
                citations = self._extract_citations(s_raw)
                for c in citations:
                    all_citations.add(c)

                links = self._extract_links(s_raw)
                for link in links:
                    all_links.add(link)

                quotes = self._extract_quotes(s_raw)
                for q in quotes:
                    all_quotes.append({
                        "section_id": section_id,
                        "paragraph_index": p_idx,
                        "sentence_index": s_idx,
                        "quote_text": q,
                    })

                parsed_sentences.append(
                    ParsedSentence(
                        sentence_index=s_idx,
                        text=s_raw,
                        is_heading=False,
                        is_quote=len(quotes) > 0,
                        citations=citations,
                    )
                )

            parsed_paragraphs.append(
                ParsedParagraph(
                    paragraph_index=p_idx,
                    text=p_raw,
                    sentences=parsed_sentences,
                )
            )

        return ParsedSection(
            section_id=section_id,
            heading=heading,
            level=level,
            paragraphs=parsed_paragraphs,
            raw_content=raw_text,
        )

    def _split_sentences(self, text: str) -> list[str]:
        """Splits paragraph text into sentences using punctuation boundaries."""
        # Simple regex-based sentence splitter preserving periods within abbreviations/numbers
        pattern = r"(?<=[.!?])\s+(?=[A-Z0-9\"'“‘])"
        parts = re.split(pattern, text.strip())
        return [p.strip() for p in parts if p.strip()]

    def _extract_citations(self, text: str) -> list[str]:
        """Extracts bracketed citation tags like [cite:src_123], [src_123], [1], or [Source: XYZ]."""
        found: list[str] = []
        # Matches [cite:src_xxx], [source_xxx], [src_xxx], [uuid], [1], etc.
        pattern = r"\[(?:cite:)?([a-zA-Z0-9_\-]+)\]"
        matches = re.findall(pattern, text)
        for m in matches:
            found.append(m.strip())
        return found

    def _extract_links(self, text: str) -> list[str]:
        """Extracts markdown links [anchor](url) and bare URLs."""
        found: list[str] = []
        markdown_links = re.findall(r"\[.*?\]\((https?://[^\s\)]+)\)", text)
        bare_urls = re.findall(r"(?<!\()(https?://[^\s\)]+)", text)
        found.extend(markdown_links)
        found.extend(bare_urls)
        return found

    def _extract_quotes(self, text: str) -> list[str]:
        """Extracts text enclosed in double or smart quotes."""
        pattern = r'["“]([^"”]{4,})["”]'
        matches = re.findall(pattern, text)
        return [m.strip() for m in matches]
