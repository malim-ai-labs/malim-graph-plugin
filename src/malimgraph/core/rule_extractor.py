"""Rule-based entity extraction using regex patterns with citation context."""

from __future__ import annotations

import re
from dataclasses import dataclass

from malimgraph.core.pdf_reader import DocumentContent, PageContent
from malimgraph.schemas.entities import Citation, Confidence, Entity, ExtractionMethod
from malimgraph.utils.hashing import entity_id
from malimgraph.utils.text import extract_snippet


@dataclass
class RuleMatch:
    label: str
    entity_type: str
    page_number: int
    snippet: str
    start: int
    end: int


# Each pattern: (name, entity_type, regex)
PATTERNS: list[tuple[str, str, re.Pattern]] = [
    (
        "date_full",
        "Date",
        re.compile(
            r"\b(?:January|February|March|April|May|June|July|August|September|October|"
            r"November|December)\s+\d{1,2},?\s+\d{4}\b",
            re.IGNORECASE,
        ),
    ),
    (
        "date_numeric",
        "Date",
        re.compile(r"\b\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}\b"),
    ),
    (
        "email",
        "Email",
        re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Z|a-z]{2,}\b"),
    ),
    (
        "url",
        "URL",
        re.compile(r"https?://[^\s\)\]\>\"\']+", re.IGNORECASE),
    ),
    (
        "monetary_amount",
        "MonetaryAmount",
        re.compile(
            r"(?:USD|MYR|RM|EUR|GBP|SGD|\$|€|£)\s*[\d,]+(?:\.\d{2})?(?:\s*(?:million|billion|thousand|M|B|K))?",
            re.IGNORECASE,
        ),
    ),
    (
        "percentage",
        "Percentage",
        re.compile(r"\b\d+(?:\.\d+)?%\b"),
    ),
    (
        "legal_act",
        "LegalReference",
        re.compile(
            r"\b(?:Act|Regulation|Directive|Ordinance|Enactment|By-?law)\s+(?:No\.?\s*)?\d+[\w\s]*\b",
            re.IGNORECASE,
        ),
    ),
    (
        "company_number",
        "CompanyRegistration",
        re.compile(
            r"\b(?:Reg(?:istration)?\.?\s*No\.?|SSM|CCM)\s*[:\-]?\s*[\d\-]+\b", re.IGNORECASE
        ),
    ),
    (
        "ic_number",
        "IdentificationNumber",
        re.compile(r"\b\d{6}[‐\-]\d{2}[‐\-]\d{4}\b"),
    ),
    (
        "phone",
        "PhoneNumber",
        re.compile(r"\b(?:\+?60|0)[\s\-]?\d{1,2}[\s\-]?\d{6,8}\b"),
    ),
    (
        "section_reference",
        "SectionReference",
        re.compile(r"\b[Ss]ection\s+\d+(?:\.\d+)*(?:\([a-z]\))?\b"),
    ),
    (
        "clause_reference",
        "ClauseReference",
        re.compile(r"\b[Cc]lause\s+\d+(?:\.\d+)*(?:\([a-z]\))?\b"),
    ),
    (
        "article_reference",
        "ArticleReference",
        re.compile(r"\b[Aa]rticle\s+\d+(?:\.\d+)?\b"),
    ),
    (
        "year",
        "Year",
        re.compile(r"\b(?:19|20)\d{2}\b"),
    ),
]


def extract_by_rules(doc: DocumentContent) -> list[Entity]:
    """
    Run all regex patterns over every page and return Entity objects with
    citation provenance (source_text, source_pages, chunk_id).
    """
    entity_map: dict[str, Entity] = {}

    for page in doc.pages:
        matches = _find_matches_in_page(page)
        for match in matches:
            eid = entity_id(match.entity_type, match.label)
            citation = Citation(
                text=match.snippet,
                pages=[match.page_number],
                chunk_id=f"page_{match.page_number}",
                extraction_method=ExtractionMethod.RULE,
            )

            if eid in entity_map:
                existing = entity_map[eid]
                if match.page_number not in existing.source_pages:
                    existing.source_pages.append(match.page_number)
                existing.citations.append(citation)
                # Upgrade confidence if seen on multiple pages
                if len(existing.source_pages) >= 2:
                    existing.confidence = Confidence.HIGH
            else:
                entity_map[eid] = Entity(
                    id=eid,
                    label=match.label,
                    type=match.entity_type,
                    extraction_method=ExtractionMethod.RULE,
                    confidence=Confidence.HIGH,
                    source_pages=[match.page_number],
                    source_text=match.snippet,
                    source_chunk_id=f"page_{match.page_number}",
                    source_chunk_ids=[f"page_{match.page_number}"],
                    citations=[citation],
                )

    return list(entity_map.values())


def _find_matches_in_page(page: PageContent) -> list[RuleMatch]:
    matches = []
    text = page.text

    for _, entity_type, pattern in PATTERNS:
        for m in pattern.finditer(text):
            label = m.group(0).strip()
            if not label or len(label) < 2:
                continue
            snippet = extract_snippet(text, m.start(), m.end(), context=100)
            matches.append(
                RuleMatch(
                    label=label,
                    entity_type=entity_type,
                    page_number=page.page_number,
                    snippet=snippet,
                    start=m.start(),
                    end=m.end(),
                )
            )

    return matches
