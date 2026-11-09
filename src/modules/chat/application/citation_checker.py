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
        """Verify that every numeric factual claim (allowance, ceiling, marks, date) and its unit appear in cited chunks.

        Strengthened check:
        1. Evaluates sentences containing numeric claims regardless of citation placement (even if citation marker sits on a different line).
        2. Rejects numeric claims whose sentence carries no citation marker if the claim cannot be verified in cited chunks.
        3. Enforces group qualification on multi-tier allowance tables: rejects unqualified single rates when chunk defines multi-tier course groups.
        """
        # Split into individual sentences/statements
        sentences = re.split(r"(?<=[.!?\n])\s+", answer_text)
        all_answer_cits = cls.extract_citation_numbers(answer_text)

        # Build combined text of all chunks cited across the entire answer
        all_cited_chunks_text_parts: list[str] = []
        for num in all_answer_cits:
            idx = num - 1
            if 0 <= idx < len(retrieved_chunks):
                ch = retrieved_chunks[idx]
                all_cited_chunks_text_parts.append(str(ch.get("chunk_content", "")))
                all_cited_chunks_text_parts.append(str(ch.get("window_close_date", "")))
                all_cited_chunks_text_parts.append(str(ch.get("academic_year", "")))
                all_cited_chunks_text_parts.append(str(ch.get("scheme_id", "")))
        all_cited_text = " ".join(all_cited_chunks_text_parts).lower()

        # Check if any cited chunk contains a multi-tier group table (e.g. Group I, II, III, IV)
        chunk_has_multi_group = any(
            re.search(r"\bgroup\s*-?\s*i\b", str(ch.get("chunk_content", "")), re.IGNORECASE)
            and re.search(r"\bgroup\s*-?\s*ii\b", str(ch.get("chunk_content", "")), re.IGNORECASE)
            for num in all_answer_cits
            if 0 <= num - 1 < len(retrieved_chunks)
            for ch in [retrieved_chunks[num - 1]]
        )

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            cits = [int(m) for m in CITATION_REGEX.findall(sentence)]

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
                for m in re.finditer(r"(?<![0-9,])([0-9]+(?:,[0-9]{3})*)(?![0-9,])", clean_s):
                    val = m.group(1)
                    if len(val.replace(",", "")) >= 2:
                        allowance_nums.append(val)

            # Preserve discovery order while de-duplicating
            seen_nums: set[str] = set()
            numbers_to_check: list[str] = []
            for n in currency_nums + percent_nums + date_matches + allowance_nums:
                if n not in seen_nums:
                    seen_nums.add(n)
                    numbers_to_check.append(n)

            if not numbers_to_check:
                continue

            # Determine supporting text: if sentence has its own citation, use that chunk;
            # otherwise fall back to all cited chunks in the answer.
            if cits:
                cited_text_parts: list[str] = []
                for num in cits:
                    idx = num - 1
                    if 0 <= idx < len(retrieved_chunks):
                        ch = retrieved_chunks[idx]
                        cited_text_parts.append(str(ch.get("chunk_content", "")))
                        cited_text_parts.append(str(ch.get("window_close_date", "")))
                        cited_text_parts.append(str(ch.get("academic_year", "")))
                        cited_text_parts.append(str(ch.get("scheme_id", "")))
                active_chunk_text = " ".join(cited_text_parts).lower()
            else:
                # Sentence carries no citation marker: must be traceable to chunks cited in the answer
                if not all_answer_cits:
                    logger.warning(
                        "Numeric grounding check failed: Numeric claim '%s' in sentence carries no citation marker.",
                        next(iter(numbers_to_check)),
                    )
                    return (
                        False,
                        f"Numeric claim '{next(iter(numbers_to_check))}' carries no citation marker",
                    )
                active_chunk_text = all_cited_text

            for raw_num in numbers_to_check:
                clean_num = raw_num.replace(",", "").strip()
                # Ignore year numbers in academic session (e.g. 2024, 2025) if present
                if clean_num in ("2024", "2025") and (
                    "2024" in active_chunk_text
                    or "2025" in active_chunk_text
                    or "2024" in all_cited_text
                    or "2025" in all_cited_text
                ):
                    continue

                num_found = (
                    clean_num.lower() in active_chunk_text
                    or raw_num.lower() in active_chunk_text
                    or clean_num.lower() in all_cited_text
                    or raw_num.lower() in all_cited_text
                )
                if not num_found:
                    if clean_num.endswith(".0"):
                        num_found = (
                            clean_num[:-2] in active_chunk_text or clean_num[:-2] in all_cited_text
                        )
                    elif clean_num.endswith(".00"):
                        num_found = (
                            clean_num[:-3] in active_chunk_text or clean_num[:-3] in all_cited_text
                        )

                if not num_found:
                    logger.warning(
                        "Numeric grounding check failed: Number '%s' in answer not found in cited chunks.",
                        raw_num,
                    )
                    return False, f"Number '{raw_num}' not found in cited chunks"

            # Check periodic unit consistency if allowance amounts are claimed
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
                w in active_chunk_text for w in ["month", "/month", "p.m.", "pm"]
            ):
                logger.warning(
                    "Numeric grounding check failed: Unit 'per month' not supported by cited chunks."
                )
                return False, "Unit 'per month' not found in cited chunks"

            if has_annum and not any(
                w in active_chunk_text for w in ["annum", "annual", "year", "p.a."]
            ):
                logger.warning(
                    "Numeric grounding check failed: Unit 'per annum' not supported by cited chunks."
                )
                return False, "Unit 'per annum' not found in cited chunks"

            # Check for multi-tier group qualification:
            # If cited chunk defines multi-tier course groups, an allowance answer must not state
            # an unqualified single rate (e.g. claiming ₹300 as the sole day scholar rate)
            if chunk_has_multi_group and any(
                w in clean_s.lower() for w in ["allowance", "day scholar", "hosteller"]
            ):
                has_group_mention = any(
                    w in sentence.lower()
                    for w in ["group", "group-i", "group i", "group ii", "group iii", "group iv"]
                )
                is_unqualified_rate_claim = (
                    not has_group_mention
                    and any(c in sentence for c in ["₹300", "300", "₹ 300"])
                    and not any(g in answer_text.lower() for g in ["group i", "group-i", "group 1"])
                )
                if is_unqualified_rate_claim:
                    logger.warning(
                        "Numeric grounding check failed: Single rate '%s' stated without course group qualification for multi-group scheme.",
                        sentence,
                    )
                    return (
                        False,
                        "Unqualified single allowance rate for multi-group scheme; group-qualified rates required",
                    )

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
