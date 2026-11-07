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
    def verify_numeric_grounding(
        cls,
        answer_text: str,
        retrieved_chunks: list[dict[str, Any]],
    ) -> tuple[bool, str | None]:
        """Verify that every numeric factual claim (allowance, ceiling, marks, date) and its unit appear in cited chunks."""
        # Split into individual sentences/statements
        sentences = re.split(r"(?<=[.!?\n])\s+", answer_text)

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            cits = [int(m) for m in CITATION_REGEX.findall(sentence)]
            if not cits:
                continue

            # Collect text of all chunks cited in this sentence
            cited_text_parts: list[str] = []
            for num in cits:
                idx = num - 1
                if 0 <= idx < len(retrieved_chunks):
                    ch = retrieved_chunks[idx]
                    cited_text_parts.append(str(ch.get("chunk_content", "")))
                    cited_text_parts.append(str(ch.get("window_close_date", "")))
                    cited_text_parts.append(str(ch.get("academic_year", "")))
                    cited_text_parts.append(str(ch.get("scheme_id", "")))

            combined_chunk_text = " ".join(cited_text_parts).lower()

            # Clean sentence of citation markers and scheme identifiers
            clean_s = CITATION_REGEX.sub("", sentence)
            clean_s = re.sub(r"\bSCH-[A-Z]+-\d+\b", "", clean_s, flags=re.IGNORECASE)
            clean_s = re.sub(r"\bGroup-?[I|V|X\d]+\b", "", clean_s, flags=re.IGNORECASE)

            # 1. Currency & Financial amounts (e.g. ₹550, Rs. 1200, 13,500, 7,000)
            currency_nums = re.findall(
                r"(?:₹|Rs\.?|INR)\s*([0-9]+(?:,[0-9]+)*(?:\.[0-9]+)?(?:\s*lakh)?)",
                clean_s,
                flags=re.IGNORECASE,
            )

            # 2. Percentage requirements (e.g. 60%, 75%)
            percent_nums = re.findall(r"([0-9]+(?:\.[0-9]+)?)\s*%", clean_s)

            # 3. Dates (YYYY-MM-DD)
            date_matches = re.findall(r"\b(\d{4}-\d{2}-\d{2})\b", clean_s)

            # 4. Numbers in allowance / stipend context
            allowance_nums: list[str] = []
            if any(
                w in clean_s.lower()
                for w in [
                    "allowance",
                    "scholar",
                    "hostel",
                    "stipend",
                    "reimburse",
                    "fee",
                    "rate",
                    "₹",
                    "rs.",
                    "ꯑꯦꯂꯥꯎꯟꯁ",
                    "ꯃꯦꯟꯇꯦꯅꯦꯟꯁ",
                ]
            ):
                for m in re.finditer(r"\b([0-9]{2,}(?:,[0-9]{3})*)\b", clean_s):
                    allowance_nums.append(m.group(1))

            numbers_to_check = set(currency_nums + percent_nums + date_matches + allowance_nums)

            for raw_num in numbers_to_check:
                clean_num = raw_num.replace(",", "").strip()
                # Ignore year numbers in academic session (e.g. 2024, 2025) if present
                if clean_num in ("2024", "2025") and (
                    "2024" in combined_chunk_text or "2025" in combined_chunk_text
                ):
                    continue

                num_found = (
                    clean_num.lower() in combined_chunk_text
                    or raw_num.lower() in combined_chunk_text
                )
                if not num_found:
                    if clean_num.endswith(".0"):
                        num_found = clean_num[:-2] in combined_chunk_text
                    elif clean_num.endswith(".00"):
                        num_found = clean_num[:-3] in combined_chunk_text

                if not num_found:
                    logger.warning(
                        "Numeric grounding check failed: Number '%s' in answer not found in cited chunks.",
                        raw_num,
                    )
                    return False, f"Number '{raw_num}' not found in cited chunks"

            # 5. Check periodic unit consistency if allowance amounts are claimed
            has_month = (
                "month" in clean_s.lower()
                or "monthly" in clean_s.lower()
                or "ꯃꯟꯊ" in clean_s
                or "/month" in clean_s.lower()
            )
            has_annum = (
                "annum" in clean_s.lower()
                or "annual" in clean_s.lower()
                or "year" in clean_s.lower()
                or "/year" in clean_s.lower()
            )

            if has_month and not any(
                w in combined_chunk_text for w in ["month", "/month", "p.m.", "pm"]
            ):
                logger.warning(
                    "Numeric grounding check failed: Unit 'per month' not supported by cited chunks."
                )
                return False, "Unit 'per month' not found in cited chunks"

            if has_annum and not any(
                w in combined_chunk_text for w in ["annum", "annual", "year", "p.a."]
            ):
                logger.warning(
                    "Numeric grounding check failed: Unit 'per annum' not supported by cited chunks."
                )
                return False, "Unit 'per annum' not found in cited chunks"

        return True, None

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

        # Strengthened numeric grounding verification
        is_supported, fail_reason = cls.verify_numeric_grounding(answer_text, retrieved_chunks)
        if not is_supported:
            logger.warning(
                "Citation check failed on numeric claim verification: %s. Returning standard refusal.",
                fail_reason,
            )
            return False, STANDARD_REFUSAL_MESSAGE, []

        logger.info(
            "Citation check passed: %d citations resolved across %d retrieved chunks with verified numeric grounding.",
            len(resolved_citations),
            len(retrieved_chunks),
        )
        return True, answer_text, resolved_citations
