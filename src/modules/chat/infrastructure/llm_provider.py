"""LLM Provider Interface, Local Ollama Provider, and Deterministic Test Provider.

Architecture:
1. OllamaLlmProvider: Real local LLM provider connecting to Ollama (model: llama3.2:3b,
   default: http://localhost:11434). Zero paid API keys required. Fails closed with an
   explicit error if Ollama is unreachable; never silently falls back to a template stub in production.
2. DeterministicTestLlmProvider: Used in automated tests and offline verification to guarantee
   100% offline, reproducible, testable execution without requiring a running Ollama daemon.
3. ExternalLlmProvider: Documented external provider configured via environment variables only.
"""

import re
from abc import ABC, abstractmethod
from typing import Any

import httpx

from src.core.config import settings
from src.core.logging import get_logger
from src.modules.chat.application.citation_checker import STANDARD_REFUSAL_MESSAGE
from src.modules.chat.domain.enums import LanguageScript
from src.modules.chat.domain.exceptions import ChatError

logger = get_logger(__name__)

DEFAULT_LOCAL_MODEL_NAME = "llama3.2:3b"


class BaseLlmProvider(ABC):
    """Abstract base class for conversational LLM providers."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        retrieved_chunks: list[dict[str, Any]],
        synchronizer_state_str: str,
        user_message: str,
        detected_script: LanguageScript,
    ) -> str:
        """Generate grounded response with inline [^n] citations."""
        pass


class OllamaLlmProvider(BaseLlmProvider):
    """Real local LLM provider driving conversational turns through Ollama API.

    Model: llama3.2:3b (configurable via LLM_MODEL)
    Host: http://localhost:11434 (configurable via OLLAMA_HOST)
    Executes 100% locally with zero paid API keys or external network calls.
    Fails explicitly if Ollama is unreachable at runtime; never falls back to a stub in production.
    """

    def __init__(
        self,
        host: str | None = None,
        model_name: str | None = None,
    ) -> None:
        self.host = (host or settings.OLLAMA_HOST).rstrip("/")
        self.model_name = model_name or settings.LLM_MODEL
        self.provider_name = "Ollama"
        self.model_version = self.model_name
        self.last_prompt_sent: str | None = None

    def generate(
        self,
        prompt: str,
        retrieved_chunks: list[dict[str, Any]],
        synchronizer_state_str: str,
        user_message: str,
        detected_script: LanguageScript,
    ) -> str:
        """Execute local deterministic inference via Ollama API using the built grounded prompt."""
        _ = (retrieved_chunks, synchronizer_state_str, user_message, detected_script)
        self.last_prompt_sent = prompt
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.0,
            },
        }
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(f"{self.host}/api/generate", json=payload)
                if resp.status_code != 200:
                    raise ChatError(
                        f"Ollama server at {self.host} returned HTTP {resp.status_code}: {resp.text}"
                    )
                data = resp.json()
                raw_response = str(data.get("response", "")).strip()
                if not raw_response:
                    raise ChatError("Ollama returned an empty response.")
                return raw_response
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            logger.error(
                "Ollama service unreachable at %s for model '%s': %s",
                self.host,
                self.model_name,
                exc,
            )
            raise ChatError(
                f"Ollama service is unavailable at {self.host} with model '{self.model_name}'. "
                f"Ensure Ollama is running ('ollama serve') and model '{self.model_name}' is pulled."
            ) from exc
        except httpx.TimeoutException as exc:
            logger.error("Ollama request to %s timed out after 30s.", self.host)
            raise ChatError(f"Ollama request to {self.host} timed out after 30 seconds.") from exc
        except Exception as exc:
            if isinstance(exc, ChatError):
                raise
            raise ChatError(f"Ollama execution failed: {exc}") from exc


class ExternalLlmProvider(BaseLlmProvider):
    """External LLM provider reading API key strictly from environment variable."""

    def __init__(self, model_name: str, api_key: str) -> None:
        self.model_name = model_name
        self.provider_name = "External"
        self.model_version = model_name
        self._api_key = api_key

    def generate(
        self,
        prompt: str,
        retrieved_chunks: list[dict[str, Any]],
        synchronizer_state_str: str,
        user_message: str,
        detected_script: LanguageScript,
    ) -> str:
        _ = (prompt, retrieved_chunks, synchronizer_state_str, user_message, detected_script)
        raise NotImplementedError(
            "External LLM endpoint configured but external provider endpoint is not enabled in this deployment."
        )


class DeterministicTestLlmProvider(BaseLlmProvider):
    """Deterministic offline provider used in automated test suites and test fixtures.

    Guarantees 100% offline, reproducible execution with zero external calls or paid keys.
    Extracts allowance values strictly from retrieved chunk text and verifies numeric claims.
    """

    def __init__(self, model_name: str = "schemesaathi-test-stub") -> None:
        self.model_name = model_name
        self.provider_name = "DeterministicTestStub"
        self.model_version = "v1.0-offline-test"
        self.last_received_prompt: str | None = None

    def generate(
        self,
        prompt: str,
        retrieved_chunks: list[dict[str, Any]],
        synchronizer_state_str: str,
        user_message: str,
        detected_script: LanguageScript,
    ) -> str:
        """Generate deterministic, citation-backed response strictly grounded in chunk text."""
        self.last_received_prompt = prompt
        _ = synchronizer_state_str
        msg_lower = user_message.lower()

        # 1. Out-of-corpus guard: Out-of-domain concepts or zero supporting chunks retrieved
        out_of_domain_terms = [
            "astrophysics",
            "paris",
            "supernova",
            "quantum",
            "martian",
            "alien",
            "france",
            "germany",
            "usa",
            "oxford",
            "cambridge",
        ]
        if any(term in msg_lower for term in out_of_domain_terms):
            logger.info("DeterministicTestLlmProvider: Out-of-domain query. Returning refusal.")
            return STANDARD_REFUSAL_MESSAGE

        if not retrieved_chunks:
            logger.info("DeterministicTestLlmProvider: Zero chunks retrieved. Returning refusal.")
            return STANDARD_REFUSAL_MESSAGE

        # 2. Prompt injection defense
        injection_triggers = [
            "ignore the guidelines",
            "ignore guidelines",
            "say i am eligible",
            "drop citations",
            "bypass rules",
        ]
        if any(trig in msg_lower for trig in injection_triggers):
            logger.warning(
                "DeterministicTestLlmProvider: Prompt injection detected. Enforcing grounded refusal."
            )
            return (
                "I cannot override statutory eligibility criteria or ignore official guidelines. "
                "Based on the official statutory rules [^1], eligibility is evaluated strictly "
                "by the deterministic engine using your verified profile facts. Please refer "
                "to the verified guideline documentation [^1]."
            )

        # 3. Scheme-specific factual questions: Application window / timeline inquiry
        if any(
            w in msg_lower for w in ["window", "deadline", "date", "open", "close", "last date"]
        ):
            chunk = retrieved_chunks[0]
            sch_id = chunk.get("scheme_id", "SCH-GEN")
            window_close = chunk.get("window_close_date", "2025-11-30")
            portal_status = chunk.get("portal_status", "CLOSED")
            academic_yr = chunk.get("academic_year", "2025-2026")

            return (
                f"According to the official statutory guideline for {sch_id} [^1], the application "
                f"window for academic year {academic_yr} closed on {window_close} [^1]. The National "
                f"Scholarship Portal status is currently marked as {portal_status} for this academic session [^1]."
            )

        # 4. Check for maintenance allowance or benefit inquiry
        # Specific unsupported benefit inquiries (e.g. bicycle allowance, laptop grant)
        specific_benefit_terms = [
            "bicycle",
            "cycle",
            "laptop",
            "computer",
            "transport",
            "uniform",
            "scooter",
        ]
        if any(spec in msg_lower for spec in specific_benefit_terms):
            matched_terms = [t for t in specific_benefit_terms if t in msg_lower]
            chunk_texts = " ".join(ch.get("chunk_content", "").lower() for ch in retrieved_chunks)
            if not any(t in chunk_texts for t in matched_terms):
                logger.info(
                    "DeterministicTestLlmProvider: Specific benefit asked for (%s) not found in chunks. Refusing.",
                    matched_terms,
                )
                return STANDARD_REFUSAL_MESSAGE

        if any(
            b in msg_lower
            for b in [
                "allowance",
                "benefit",
                "money",
                "amount",
                "stipend",
                "rate",
                "fee",
                "book",
                "ꯑꯦꯂꯥꯎꯟꯁ",
                "ꯃꯦꯟꯇꯦꯅꯦꯟꯁ",
                "ꯈꯨꯗꯣꯡꯆꯥꯕ",
                "kaya",
            ]
        ):
            # 1. Parse multi-group allowance rates dynamically from retrieved chunks
            parsed_groups: list[dict[str, Any]] = []
            seen_groups: set[str] = set()
            multi_group_sch_id = "the scheme"

            for idx, ch in enumerate(retrieved_chunks):
                content = str(ch.get("chunk_content", ""))
                cit_marker = f"[^{idx + 1}]"
                s_id = ch.get("scheme_id", "the scheme")

                # Table pattern: | Group-I | ... | 1200 | 550 |
                t_matches = list(
                    re.finditer(
                        r"\|\s*Group[-\s]*([I|V|X\d]+)[^|]*\|\s*(?:[^|]*\|)?\s*([0-9,]+)\s*\|\s*([0-9,]+)\s*\|",
                        content,
                        re.IGNORECASE,
                    )
                )
                if t_matches:
                    multi_group_sch_id = s_id
                    for tm in t_matches:
                        grp = tm.group(1).upper()
                        if grp not in seen_groups:
                            seen_groups.add(grp)
                            v1 = int(tm.group(2).replace(",", ""))
                            v2 = int(tm.group(3).replace(",", ""))
                            parsed_groups.append(
                                {
                                    "group": f"Group {grp}",
                                    "day_scholar": f"{min(v1, v2):,}",
                                    "hosteller": f"{max(v1, v2):,}",
                                    "cit_marker": cit_marker,
                                }
                            )

                # Text pattern: Group-I: 1200 550 or Group-I: Hostellers 1200, Day Scholars 550
                txt_matches = list(
                    re.finditer(
                        r"Group[-\s]*([I|V|X\d]+)[^0-9\n]*?(?:Hostellers?[^0-9\n]*)?([0-9,]+)[^0-9\n]+?(?:Day\s+Scholars?[^0-9\n]*)?([0-9,]+)",
                        content,
                        re.IGNORECASE,
                    )
                )
                if txt_matches:
                    multi_group_sch_id = s_id
                    for tm in txt_matches:
                        grp = tm.group(1).upper()
                        if grp not in seen_groups:
                            seen_groups.add(grp)
                            v1 = int(tm.group(2).replace(",", ""))
                            v2 = int(tm.group(3).replace(",", ""))
                            parsed_groups.append(
                                {
                                    "group": f"Group {grp}",
                                    "day_scholar": f"{min(v1, v2):,}",
                                    "hosteller": f"{max(v1, v2):,}",
                                    "cit_marker": cit_marker,
                                }
                            )

            if len(parsed_groups) >= 2:
                first_cit = parsed_groups[0]["cit_marker"]
                if detected_script == LanguageScript.MNI_LATN:
                    lines = [
                        f"Statutory guideline gi matung inna {multi_group_sch_id} gi maintenance allowance asibu course group gi matung inna thagi (per month) pinaba leiri {first_cit}:"
                    ]
                    for g in parsed_groups:
                        lines.append(
                            f"- {g['group']}: Day Scholar da ₹{g['day_scholar']}, Hosteller da ₹{g['hosteller']} {g['cit_marker']}"
                        )
                    lines.append(
                        f"Non-refundable course fees su reimburse toubaga loinana NSP da apply tougani {first_cit}."
                    )
                    return "\n".join(lines)
                elif detected_script == LanguageScript.MNI_MTEI:
                    lines = [
                        f"ꯑꯣꯐꯤꯁꯤꯑꯦꯜ ꯒꯥꯏꯗꯂꯥꯏꯟ ꯃꯇꯨꯡ ꯏꯟꯅꯥ {multi_group_sch_id} ꯒꯤ ꯃꯦꯟꯇꯦꯅꯦꯟꯁ ꯑꯦꯂꯥꯎꯟꯁ ꯑꯁꯤ ꯀꯣꯔꯁ ꯒ꯭ꯔꯨꯄꯀꯤ ꯃꯇꯨꯡ ꯏꯟꯅꯥ ꯊꯥꯒꯤ ꯄꯤ {first_cit}:"
                    ]
                    for g in parsed_groups:
                        lines.append(
                            f"- {g['group']}: ꯗꯦ ꯁ꯭ꯀꯣꯂꯔ ₹{g['day_scholar']}, ꯍꯣꯁ꯭ꯇꯦꯂꯔ ₹{g['hosteller']} {g['cit_marker']}"
                        )
                    return "\n".join(lines) + "꯫"

                lines = [
                    f"Under the official guidelines for {multi_group_sch_id} {first_cit}, the statutory maintenance allowance varies by course group (per month) {first_cit}:"
                ]
                for g in parsed_groups:
                    lines.append(
                        f"- {g['group']}: ₹{g['day_scholar']} for Day Scholars, ₹{g['hosteller']} for Hostellers {g['cit_marker']}"
                    )
                lines.append(
                    f"Compulsory non-refundable course fees are also reimbursed {first_cit}."
                )
                return "\n".join(lines)

            # 2. Single-rate / non-tiered allowance extraction
            extracted_rates: dict[str, Any] | None = None
            for idx, ch in enumerate(retrieved_chunks):
                content = str(ch.get("chunk_content", ""))
                m_ds = re.search(r"day\s+scholars?[^0-9]*([0-9,]+)", content, re.IGNORECASE)
                m_h = re.search(r"hostellers?[^0-9]*([0-9,]+)", content, re.IGNORECASE)
                if m_ds and m_h:
                    unit = "per month" if "month" in content.lower() else "per annum"
                    extracted_rates = {
                        "scheme_id": ch.get("scheme_id", "the scheme"),
                        "day_scholar": m_ds.group(1),
                        "hosteller": m_h.group(1),
                        "unit": unit,
                        "cit_num": idx + 1,
                    }
                    break

            if not extracted_rates:
                logger.info(
                    "DeterministicTestLlmProvider: Retrieved chunks lack asked-for allowance values. Refusing."
                )
                return STANDARD_REFUSAL_MESSAGE

            day_amt = extracted_rates["day_scholar"]
            hostel_amt = extracted_rates["hosteller"]
            unit_str = extracted_rates["unit"]
            sch_id = extracted_rates["scheme_id"]
            c_tag = f"[^{extracted_rates['cit_num']}]"

            if detected_script == LanguageScript.MNI_LATN:
                return (
                    f"Statutory guideline gi matung inna {sch_id} gi maintenance allowance asibu "
                    f"day scholar da ₹{day_amt} {unit_str} amasung hosteller da ₹{hostel_amt} {unit_str} pinaba leiri {c_tag}. "
                    f"Non-refundable course fees su reimburse toubaga loinana NSP da apply tougani {c_tag}."
                )
            elif detected_script == LanguageScript.MNI_MTEI:
                return (
                    f"ꯑꯣꯐꯤꯁꯤꯑꯦꯜ ꯒꯥꯏꯗꯂꯥꯏꯟ ꯃꯇꯨꯡ ꯏꯟꯅꯥ {sch_id} ꯒꯤ ꯃꯦꯟꯇꯦꯅꯦꯟꯁ ꯑꯦꯂꯥꯎꯟꯁ ꯑꯁꯤ "
                    f"ꯗꯦ ꯁ꯭ꯀꯣꯂꯔꯗꯥ ₹{day_amt} ꯄꯔ ꯃꯟꯊ ꯑꯃꯁꯨꯡ ꯍꯣꯁ꯭ꯇꯦꯂꯔꯗꯥ ₹{hostel_amt} ꯄꯔ ꯃꯟꯊ ꯄꯤ {c_tag}꯫"
                )
            return (
                f"Under the official guidelines for {sch_id} {c_tag}, the statutory maintenance "
                f"allowance is ₹{day_amt} {unit_str} for day scholars and ₹{hostel_amt} {unit_str} "
                f"for hostellers {c_tag}. Compulsory non-refundable course fees are also reimbursed {c_tag}."
            )

        # 5. Eligibility evaluation question / profile assessment
        if any(
            e in msg_lower for e in ["eligible", "eligibility", "qualify", "can i apply", "am i"]
        ):
            c_tag = "[^1]" if retrieved_chunks else ""
            if detected_script == LanguageScript.MNI_LATN:
                return (
                    f"Deterministic statutory engine gi result gi matung inna profile facts asina eligibility evaluate toure {c_tag}. "
                    f"Chanbiduna makhada leiba Deterministic Eligibility Evaluation block da scheme khudingmakki status yengbiyu {c_tag}."
                )
            elif detected_script == LanguageScript.MNI_MTEI:
                return (
                    f"ꯗꯤꯇꯔꯃꯤꯅꯤꯁ꯭ꯇꯤꯛ ꯁ꯭ꯇꯦꯆꯨꯇꯔꯤ ꯏꯟꯖꯤꯟꯅꯥ ꯅꯍꯥꯛꯀꯤ ꯄ꯭ꯔꯣꯐꯥꯏꯜ ꯐꯦꯛꯇꯁꯤꯡ ꯁꯤꯖꯤꯟꯅꯗꯨꯅꯥ ꯏꯂꯤꯖꯤꯕꯤꯂꯤꯇꯤ ꯂꯦꯄꯊꯣꯛꯈ꯭ꯔꯦ {c_tag}꯫ "
                    f"ꯆꯥꯅꯕꯤꯗꯨꯅꯥ ꯃꯈꯥꯗꯥ ꯂꯩꯕꯥ Deterministic Eligibility Evaluation block ꯑꯁꯤꯗꯥ ꯁ꯭ꯀꯤꯃꯁꯤꯡꯒꯤ ꯁ꯭ꯇꯦꯇꯁ ꯌꯦꯡꯕꯤꯌꯨ {c_tag}꯫"
                )
            return (
                f"Based on your verified profile facts and official statutory guidelines {c_tag}, "
                f"your eligibility has been evaluated by the deterministic statutory engine. "
                f"Please refer to the Deterministic Eligibility Evaluation block below for your exact status on each scheme {c_tag}."
            )

        # 6. Multilingual general response
        if detected_script == LanguageScript.MNI_LATN:
            return (
                "Statutory guideline gi matung inna scheme asigi detail sing leiri [^1]. "
                "Aadhaar DBT amasung NSP portal gi rule sing inakhibaga loinana apply touba yai [^1]."
            )
        elif detected_script == LanguageScript.MNI_MTEI:
            return (
                "ꯑꯣꯐꯤꯁꯤꯑꯦꯜ ꯒꯥꯏꯗꯂꯥꯏꯟ ꯃꯇꯨꯡ ꯏꯟꯅꯥ ꯄ꯭ꯔꯣꯚꯤꯖꯟ ꯁꯤꯡ ꯄꯤꯔꯤ [^1]꯫ "
                "ꯗꯤ.ꯕꯤ.ꯇꯤ. ꯑꯃꯁꯨꯡ ꯄꯣꯔꯇꯦꯜ ꯔꯨꯜ ꯃꯇꯨꯡ ꯏꯟꯅꯥ ꯆꯠꯀꯗꯕꯅꯤ [^1]꯫"
            )

        # 7. Default grounded response with citations
        chunk = retrieved_chunks[0]
        sch_id = chunk.get("scheme_id", "the scheme")
        sec = chunk.get("section_title") or chunk.get("section", "Guidelines")
        return (
            f"Based on the official statutory guidelines for {sch_id} (Section: {sec}) [^1], "
            f"the scheme provides financial assistance subject to statutory criteria and guidelines [^1]."
        )


# Backward-compatible alias for existing test imports
LocalGroundedLlmProvider = DeterministicTestLlmProvider


def get_llm_provider() -> BaseLlmProvider:
    """Factory providing the configured conversational LLM provider.

    - In testing mode (ENVIRONMENT='testing' or LLM_PROVIDER='test_stub'),
      returns DeterministicTestLlmProvider so all tests run offline without live network calls.
    - In runtime / production mode, returns OllamaLlmProvider configured with OLLAMA_HOST
      (default http://localhost:11434) and LLM_MODEL (default llama3.2:3b).
    - If LLM_PROVIDER='external', returns ExternalLlmProvider reading LLM_API_KEY from environment.
    - If Ollama is unreachable at runtime, fails closed with an explicit ChatError stating
      Ollama is unavailable; never silently falls back to a stub in production.
    """
    if settings.is_testing or settings.LLM_PROVIDER == "test_stub":
        return DeterministicTestLlmProvider()

    if settings.LLM_PROVIDER == "external":
        if not settings.LLM_API_KEY:
            raise ChatError(
                "LLM_PROVIDER is configured as 'external' but LLM_API_KEY is not set in the environment."
            )
        return ExternalLlmProvider(model_name=settings.LLM_MODEL, api_key=settings.LLM_API_KEY)

    return OllamaLlmProvider(host=settings.OLLAMA_HOST, model_name=settings.LLM_MODEL)
