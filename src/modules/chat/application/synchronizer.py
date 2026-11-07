"""Deterministic State Synchronizer.

Implements M0 roadmap state synchronization:
1. Extracts profile facts and mid-conversation corrections from user messages.
2. Updates structured UserProfileFacts in session state (never free text).
3. Injects machine-readable facts and deterministic engine results into prompt.
4. Ensures missing fields are explicitly labelled MISSING so the assistant
   never assumes values.
"""

import contextlib
import re
from typing import Any

from src.core.logging import get_logger
from src.modules.chat.domain.models import ChatSession, UserProfileFacts
from src.modules.eligibility.application.schemas import BatchEvaluationResponse

logger = get_logger(__name__)


class DeterministicStateSynchronizer:
    """Manages structured session state synchronization and prompt fact injection."""

    # Natural language extraction regexes for mid-conversation corrections
    _INCOME_REGEX = re.compile(
        r"(?:actually\s+)?(?:my\s+)?(?:family\s+)?(?:annual\s+)?income\s*(?:is|:|=)?\s*[₹Rs\.]*\s*([0-9]+(?:,[0-9]+)*(?:\.[0-9]+)?)\s*(lakh(?:s)?)?",
        re.IGNORECASE,
    )
    _MARKS_REGEX = re.compile(
        r"(?:my\s+)?(?:marks|score|percentage)\s*(?:is|:|=)?\s*([0-9]+(?:\.[0-9]+)?)\s*%?",
        re.IGNORECASE,
    )
    _CATEGORY_REGEX = re.compile(
        r"\b(?:category|caste)\s*(?:is|:|=)?\s*(ST|SC|OBC|GENERAL|GEN)\b|\bi\s+am\s+(?:an?\s+)?(ST|SC|OBC)\b",
        re.IGNORECASE,
    )
    _DISPLACED_REGEX = re.compile(
        r"\b(displaced|not\s+displaced|non-displaced)\b",
        re.IGNORECASE,
    )
    _COURSE_REGEX = re.compile(
        r"\b(?:course|studying|class)\s*(?:is|in|for|:|=)?\s*(UNDERGRADUATE|POSTGRADUATE|POST_MATRIC|CLASS_9_10|DIPLOMA|UG|PG|CLASS\s*10|CLASS\s*9)\b|\b(UNDERGRADUATE|POSTGRADUATE|DIPLOMA|UG|PG)\s+course\b",
        re.IGNORECASE,
    )
    _DOMICILE_REGEX = re.compile(
        r"\b(?:domicile(?:\s+state)?|resident\s+of)\s*(?:is|in|:|=)?\s*([A-Za-z]+)\b|\b(?:state)\s*(?:is|:|=)\s*([A-Za-z]+)\b|\b(?:from)\s+(MANIPUR|ASSAM|NAGALAND|MEGHALAYA|TRIPURA|MIZORAM|ARUNACHAL|DELHI|BIHAR|KERALA|PUNJAB)\b",
        re.IGNORECASE,
    )

    @classmethod
    def extract_profile_updates(cls, text: str) -> dict[str, Any]:
        """Extract explicit profile fact updates from natural language user message."""
        updates: dict[str, Any] = {}

        # 1. Income update
        inc_m = cls._INCOME_REGEX.search(text)
        if inc_m:
            num_str = inc_m.group(1).replace(",", "").strip()
            is_lakh = bool(inc_m.group(2))
            with contextlib.suppress(ValueError):
                num = float(num_str)
                updates["annual_family_income_inr"] = num * 100000.0 if is_lakh else num

        # 2. Marks update
        marks_m = cls._MARKS_REGEX.search(text)
        if marks_m:
            with contextlib.suppress(ValueError):
                updates["marks_percent"] = float(marks_m.group(1))

        # 3. Category update
        cat_m = cls._CATEGORY_REGEX.search(text)
        if cat_m:
            raw_cat = (cat_m.group(1) or cat_m.group(2)).upper()
            if raw_cat == "GEN":
                raw_cat = "GENERAL"
            updates["social_category"] = raw_cat

        # 4. Displaced status update
        disp_m = cls._DISPLACED_REGEX.search(text)
        if disp_m:
            phrase = disp_m.group(1).lower()
            updates["is_displaced"] = not ("not" in phrase or "non" in phrase)

        # 5. Course level update
        course_m = cls._COURSE_REGEX.search(text)
        if course_m:
            matched = course_m.group(1) or course_m.group(2)
            raw_c = matched.upper().replace(" ", "_")
            if raw_c == "UG":
                raw_c = "UNDERGRADUATE"
            elif raw_c == "PG":
                raw_c = "POSTGRADUATE"
            elif raw_c in ("CLASS_9", "CLASS_10"):
                raw_c = "CLASS_9_10"
            updates["course_level"] = raw_c

        # 6. Domicile state update
        dom_m = cls._DOMICILE_REGEX.search(text)
        if dom_m:
            raw_dom = dom_m.group(1) or dom_m.group(2) or dom_m.group(3)
            if raw_dom:
                dom = raw_dom.upper()
                if dom not in (
                    "A",
                    "THE",
                    "IS",
                    "MY",
                    "IN",
                    "MERIT",
                    "SECTOR",
                    "CENTRAL",
                    "SCHOLARSHIP",
                    "LEVEL",
                    "GOVERNMENT",
                ):
                    updates["domicile_state"] = dom

        return updates

    @classmethod
    def apply_updates(
        cls, session: ChatSession, updates: dict[str, Any] | None = None, message_text: str = ""
    ) -> list[str]:
        """Apply explicit and extracted profile updates to session state."""
        merged_updates: dict[str, Any] = {}
        if updates:
            merged_updates.update(updates)

        if message_text:
            extracted = cls.extract_profile_updates(message_text)
            merged_updates.update(extracted)

        if merged_updates:
            changed = session.profile_facts.update_from_dict(merged_updates)
            if changed:
                logger.info(
                    "DeterministicStateSynchronizer updated session %s fields: %s",
                    session.session_id,
                    changed,
                )
            return changed
        return []

    @classmethod
    def serialize_synchronizer_state(
        cls,
        facts: UserProfileFacts,
        eligibility_eval: BatchEvaluationResponse | None = None,
    ) -> str:
        """Serialize state into machine-readable prompt block outranking conversation history."""
        lines = [
            "=== DETERMINISTIC SYNCHRONIZER STATE (ABSOLUTE GROUND TRUTH) ===",
            "[USER PROFILE FACTS]",
        ]

        missing_fields: list[str] = []

        if facts.domicile_state:
            lines.append(f"- Domicile State: {facts.domicile_state.upper()}")
        else:
            missing_fields.append("domicile_state")
            lines.append("- Domicile State: [MISSING]")

        if facts.social_category:
            lines.append(f"- Social Category: {facts.social_category.upper()}")
        else:
            missing_fields.append("social_category")
            lines.append("- Social Category: [MISSING]")

        if facts.annual_family_income_inr is not None:
            lines.append(f"- Annual Family Income: ₹{facts.annual_family_income_inr:,.2f}")
        else:
            missing_fields.append("annual_family_income_inr")
            lines.append("- Annual Family Income: [MISSING]")

        if facts.marks_percent is not None:
            lines.append(f"- Qualifying Marks Percent: {facts.marks_percent:.2f}%")
        else:
            missing_fields.append("marks_percent")
            lines.append("- Qualifying Marks Percent: [MISSING]")

        if facts.course_level:
            lines.append(f"- Course Level: {facts.course_level.upper()}")
        else:
            missing_fields.append("course_level")
            lines.append("- Course Level: [MISSING]")

        if facts.gender:
            lines.append(f"- Gender: {facts.gender.upper()}")
        else:
            lines.append("- Gender: ANY / NOT_SPECIFIED")

        if facts.is_displaced is not None:
            lines.append(
                f"- Conflict Displaced Status: {'YES (Displaced)' if facts.is_displaced else 'NO (Non-Displaced)'}"
            )
        else:
            missing_fields.append("is_displaced")
            lines.append("- Conflict Displaced Status: [MISSING]")

        if missing_fields:
            lines.append(f"- Unsupplied Required Fields: {', '.join(missing_fields)}")

        if eligibility_eval:
            lines.append("\n[DETERMINISTIC ELIGIBILITY RESULTS]")
            lines.append(
                "(Computed strictly by Statutory AST Rule Engine. Outranks all conversation history.)"
            )
            for item in eligibility_eval.schemes:
                status_str = item.overall_outcome.value.upper()
                reason_str = (
                    "; ".join(item.ineligibility_reasons)
                    if item.ineligibility_reasons
                    else "Criteria satisfied."
                )
                lines.append(
                    f"- {item.scheme_id} ({item.scheme_title}): {status_str} — {reason_str}"
                )

        lines.append("=== END SYNCHRONIZER STATE ===")
        return "\n".join(lines)
