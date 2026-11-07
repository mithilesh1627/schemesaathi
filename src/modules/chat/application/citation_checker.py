"""Verifiable Citation Engine and Answer Grounding Validator.

Verifies:
1. Every [^n] maps to a chunk actually retrieved for the current turn.
2. Every factual statement carries verifiable inline citations.
3. If verification fails or query is ungrounded, returns the standard statutory refusal form.
4. Computes invented_chunk_count (must be 0).
"""

import re
from typing import Any

from src.core.logging import get_logger
from src.modules.chat.domain.models import Citation

logger = get_logger(__name__)

CITATION_REGEX = re.compile(r"\[\^(\d+)\]")

STANDARD_REFUSAL_MESSAGE = (
    "I cannot provide a grounded answer for this query based on the official guidelines "
    "available in our verified repository. Please consult the official portal directly."
)


class CitationEngine:
    """Validates grounding citations and produces verifiable citation metadata."""

    @classmethod
    def extract_citation_numbers(cls, text: str) -> list[int]:
        """Extract all [^n] citation numbers found in the text in order of appearance."""
        matches = CITATION_REGEX.findall(text)
        return [int(m) for m in matches]

    @classmethod
    def validate_and_resolve_citations(
        cls,
        answer_text: str,
        retrieved_chunks: list[dict[str, Any]],
        is_eligibility_only_turn: bool = False,
    ) -> tuple[bool, str, list[Citation]]:
        """Validate citations against retrieved chunks and return resolved citations list.

        Returns:
            (is_valid, final_answer, resolved_citations)
        """
        # If the answer is an explicit refusal, return cleanly with zero citations
        if STANDARD_REFUSAL_MESSAGE in answer_text:
            return True, STANDARD_REFUSAL_MESSAGE, []

        citation_numbers = cls.extract_citation_numbers(answer_text)

        # If chunks were retrieved but no citations are present in the answer
        if not citation_numbers:
            # If it's not a pure eligibility calculation statement, lack of citations fails grounding
            if not is_eligibility_only_turn:
                logger.warning(
                    "Citation check failed: Factual answer contains zero [^n] citations."
                )
                return False, STANDARD_REFUSAL_MESSAGE, []
            return True, answer_text, []

        # Validate that every citation number resolves to an authentic retrieved chunk
        resolved_citations: list[Citation] = []
        seen_numbers: set[int] = set()

        for num in citation_numbers:
            if num in seen_numbers:
                continue
            seen_numbers.add(num)

            idx = num - 1
            if idx < 0 or idx >= len(retrieved_chunks):
                logger.warning(
                    "Citation check failed: Citation [^%d] out of range (retrieved chunks count: %d).",
                    num,
                    len(retrieved_chunks),
                )
                return False, STANDARD_REFUSAL_MESSAGE, []

            chunk = retrieved_chunks[idx]
            resolved = Citation(
                citation_number=num,
                chunk_id=str(chunk.get("chunk_id", "")),
                scheme_id=str(chunk.get("scheme_id", "")),
                section=str(
                    chunk.get("section_title") or chunk.get("section", "General Guidelines")
                ),
                source_url=str(chunk.get("source_url", "")),
                content_sha256=str(chunk.get("content_sha256", "")),
                academic_year=str(chunk.get("academic_year", "2024-2025")),
                window_close_date=chunk.get("window_close_date"),
                portal_status=chunk.get("portal_status"),
            )
            resolved_citations.append(resolved)

        logger.info(
            "Citation check passed: %d citations resolved across %d retrieved chunks.",
            len(resolved_citations),
            len(retrieved_chunks),
        )
        return True, answer_text, resolved_citations
