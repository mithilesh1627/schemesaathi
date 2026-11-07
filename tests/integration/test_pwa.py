"""Integration and Verification Tests for SchemeSaathi Sprint 5 PWA Shell.

Verifies:
1. Payload budget test: Asserts real served initial payload (HTML + CSS + JS + manifest + sw + icons) <= 120 KB (target < 115 KB).
2. Offline checklist persistence: Asserts service worker caching, IndexedDB persistence logic, and statutory warnings.
3. Eligibility flow: Asserts PWA evaluation returns 2/4/0 (non-displaced) and 3/3/0 (displaced; SCH-MN-003 flips).
4. Chat flow: Asserts chat answers with link citations, separate eligibility block, and plain-language Ollama error.
5. Language switch: Asserts English and Romanized Meiteilon (mni-Latn) dictionary completeness and UI rendering.
6. Zero-Aadhaar policy: Asserts zero Aadhaar fields in PWA, and client-side pre-flight redaction of 12-digit numbers.
7. Pan-India guardrail: Asserts non-Manipur scheme evaluation and state-agnostic form design.
"""

import re

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.infrastructure.seed_data import seed_pilot_schemes
from src.modules.retrieval.application.corpus_seed_service import CorpusSeedService


@pytest.fixture(autouse=True)
async def setup_pwa_test_corpus(db_session: AsyncSession) -> None:
    """Ensure pilot schemes and guideline corpus are seeded before PWA tests."""
    await seed_pilot_schemes(db_session)
    seeder = CorpusSeedService(db_session)
    await seeder.seed_guideline_corpus()


@pytest.mark.asyncio
async def test_pwa_payload_budget_under_120kb(async_client: AsyncClient) -> None:
    """Requirement 3: Assert real served initial payload <= 120 KB (M0 target < 115 KB)."""
    # 1. Fetch PWA shell HTML
    res_html = await async_client.get("/")
    assert res_html.status_code == 200
    html_bytes = len(res_html.content)

    # 2. Fetch manifest.json
    res_manifest = await async_client.get("/manifest.json")
    assert res_manifest.status_code == 200
    assert "application/manifest+json" in res_manifest.headers.get("content-type", "")
    manifest_bytes = len(res_manifest.content)

    # 3. Fetch service worker
    res_sw = await async_client.get("/sw.js")
    assert res_sw.status_code == 200
    assert "application/javascript" in res_sw.headers.get("content-type", "")
    assert res_sw.headers.get("service-worker-allowed") == "/"
    sw_bytes = len(res_sw.content)

    # 4. Fetch CSS
    res_css = await async_client.get("/static/app.css")
    assert res_css.status_code == 200
    css_bytes = len(res_css.content)

    # 5. Fetch JS
    res_js = await async_client.get("/static/app.js")
    assert res_js.status_code == 200
    js_bytes = len(res_js.content)

    # 6. Fetch Icons (loaded on first paint / manifest)
    res_icon_svg = await async_client.get("/static/icons/icon-192.svg")
    assert res_icon_svg.status_code == 200
    icon_svg_bytes = len(res_icon_svg.content)

    res_icon_png = await async_client.get("/static/icons/icon-192.png")
    assert res_icon_png.status_code == 200
    icon_png_bytes = len(res_icon_png.content)

    res_icon512_png = await async_client.get("/static/icons/icon-512.png")
    assert res_icon512_png.status_code == 200
    icon512_png_bytes = len(res_icon512_png.content)

    total_initial_bytes = (
        html_bytes
        + manifest_bytes
        + sw_bytes
        + css_bytes
        + js_bytes
        + icon_svg_bytes
        + icon_png_bytes
        + icon512_png_bytes
    )

    # Hard budget: <= 120 KB (122,880 bytes)
    # M0 Target: < 115 KB (117,760 bytes)
    max_budget_bytes = 120 * 1024
    m0_target_bytes = 115 * 1024

    assert total_initial_bytes <= max_budget_bytes, (
        f"Initial payload {total_initial_bytes} bytes exceeds hard budget of {max_budget_bytes} bytes"
    )
    assert total_initial_bytes < m0_target_bytes, (
        f"Initial payload {total_initial_bytes} bytes exceeds M0 target of {m0_target_bytes} bytes"
    )

    # Verify no external CDN or third-party fonts are imported in HTML or CSS
    html_text = res_html.text.lower()
    css_text = res_css.text.lower()
    for forbidden in ["jsdelivr.net", "unpkg.com", "fonts.googleapis.com", "cdnjs.cloudflare.com"]:
        assert forbidden not in html_text, f"Forbidden CDN URL found in HTML: {forbidden}"
        assert forbidden not in css_text, f"Forbidden CDN URL found in CSS: {forbidden}"


@pytest.mark.asyncio
async def test_pwa_offline_checklist_and_service_worker_spec(
    async_client: AsyncClient,
) -> None:
    """Requirement 2: Service worker specification, IndexedDB persistence, and statutory warnings."""
    # Verify Service Worker contents
    res_sw = await async_client.get("/sw.js")
    assert res_sw.status_code == 200
    sw_code = res_sw.text

    assert "schemesaathi-shell-v1" in sw_code
    assert "caches.open" in sw_code
    assert "self.skipWaiting()" in sw_code
    assert "clients.claim()" in sw_code
    assert "/static/app.css" in sw_code
    assert "/static/app.js" in sw_code

    # Verify App JS IndexedDB checklist persistence logic
    res_js = await async_client.get("/static/app.js")
    assert res_js.status_code == 200
    js_code = res_js.text

    assert "schemesaathi_pwa" in js_code
    assert "checklist_store" in js_code
    assert "openIndexedDb" in js_code
    assert "saveStoredChecklist" in js_code
    assert "clearAllIndexedDb" in js_code
    assert "clear-data-btn" in js_code

    # Verify Statutory Warning content in HTML
    res_html = await async_client.get("/")
    assert res_html.status_code == 200
    html_text = res_html.text

    # NPCI APB Warning presence
    assert "NPCI" in html_text
    assert "Payment Bridge" in html_text or "APB" in html_text
    assert "PFMS DBT" in html_text or "disbursement" in html_text

    # NSP OTR Face RD Warning presence
    assert "OTR" in html_text or "One-Time Registration" in html_text
    assert "Face RD" in html_text


@pytest.mark.asyncio
async def test_pwa_eligibility_flow_demo_profiles(async_client: AsyncClient) -> None:
    """Requirement 1: Check Eligibility form evaluates 2/4/0 (non-displaced) and 3/3/0 (displaced)."""
    # 1. Non-displaced ST Manipur profile
    non_displaced_payload = {
        "domicile_state": "MANIPUR",
        "social_category": "ST",
        "annual_family_income_inr": 200000.0,
        "marks_percent": 65.0,
        "course_level": "UNDERGRADUATE",
        "is_displaced": False,
    }

    resp1 = await async_client.post("/api/v1/eligibility/evaluate", json=non_displaced_payload)
    assert resp1.status_code == 200
    data1 = resp1.json()

    assert data1["total_eligible"] == 2
    assert data1["total_not_eligible"] == 4
    assert data1["total_unknown"] == 0

    schemes1 = {s["scheme_id"]: s for s in data1["schemes"]}
    assert schemes1["SCH-MN-005"]["overall_outcome"] == "ELIGIBLE"  # Post-Matric ST
    assert schemes1["SCH-MN-001"]["overall_outcome"] == "ELIGIBLE"  # Merit Stipend
    assert schemes1["SCH-MN-003"]["overall_outcome"] == "NOT_ELIGIBLE"  # Displaced scheme fails

    # Verify official source URLs and portal statuses
    for s in data1["schemes"]:
        assert s["official_source_url"].startswith("http")

    # 2. Displaced ST Manipur profile (SCH-MN-003 flips to ELIGIBLE)
    displaced_payload = dict(non_displaced_payload)
    displaced_payload["is_displaced"] = True

    resp2 = await async_client.post("/api/v1/eligibility/evaluate", json=displaced_payload)
    assert resp2.status_code == 200
    data2 = resp2.json()

    assert data2["total_eligible"] == 3
    assert data2["total_not_eligible"] == 3
    assert data2["total_unknown"] == 0

    schemes2 = {s["scheme_id"]: s for s in data2["schemes"]}
    assert schemes2["SCH-MN-003"]["overall_outcome"] == "ELIGIBLE"  # Displaced scheme satisfied


@pytest.mark.asyncio
async def test_pwa_chat_flow_citations_and_error_handling(
    async_client: AsyncClient,
) -> None:
    """Requirement 1: Grounded chat answers with linkable citations, separate eligibility block, and plain-language errors."""
    session_id = "test-pwa-chat-01"

    # 1. Ask factual question about Post-Matric ST
    req = {
        "session_id": session_id,
        "message": "What is the maintenance allowance for Post-Matric ST day scholars?",
    }

    resp = await async_client.post("/api/v1/chat/message", json=req)
    assert resp.status_code == 200
    data = resp.json()

    assert data["invented_chunk_count"] == 0
    assert len(data["citations"]) > 0

    # Verify authentic figures in answer
    assert "550" in data["answer"]
    assert "month" in data["answer"].lower()

    # Verify citation link structure
    cit = data["citations"][0]
    assert cit["scheme_id"] == "SCH-MN-005"
    assert cit["source_url"].startswith("http")
    assert cit["academic_year"] == "2024-2025"
    assert cit["window_close_date"] == "2024-11-30"

    # 2. Verify plain-language Ollama error in PWA client JS
    res_js = await async_client.get("/static/app.js")
    assert res_js.status_code == 200
    assert "errorOllamaDown" in res_js.text
    assert "fail-closed" in res_js.text.lower()
    assert "chat-retry-btn" in res_js.text


@pytest.mark.asyncio
async def test_pwa_language_switch_meiteilon(async_client: AsyncClient) -> None:
    """Requirement 1: UI switches between English and Romanized Meiteilon (mni-Latn)."""
    res_js = await async_client.get("/static/app.js")
    assert res_js.status_code == 200
    js_text = res_js.text

    # Assert Romanized Meiteilon translations are defined
    assert "Bharatki Scholarship Thiheibagi Platform" in js_text
    assert "Eligibility Yengba" in js_text
    assert "SchemeSaathi-da Hangba" in js_text
    assert "Eigi Document-sing" in js_text
    assert "NPCI APB Mapping Taba Tangai" in js_text
    assert "Eigi Data Mutthatpu" in js_text

    # Assert visible language toggle in HTML
    res_html = await async_client.get("/")
    assert res_html.status_code == 200
    assert 'id="lang-toggle"' in res_html.text


@pytest.mark.asyncio
async def test_pwa_zero_aadhaar_policy_and_client_redaction(
    async_client: AsyncClient,
) -> None:
    """Requirement 1: No Aadhaar fields exist, and 12-digit number is redacted client-side."""
    res_html = await async_client.get("/")
    assert res_html.status_code == 200
    html_text = res_html.text

    # Assert no form input or label asks for Aadhaar number
    inputs = re.findall(r"<input[^>]+>", html_text, re.IGNORECASE)
    for inp in inputs:
        assert "aadhaar" not in inp.lower()
        assert "uidai" not in inp.lower()

    # Assert client-side pre-flight redaction in app.js
    res_js = await async_client.get("/static/app.js")
    assert res_js.status_code == 200
    js_text = res_js.text
    assert "redactAadhaarClientSide" in js_text
    assert "[AADHAAR REDACTED]" in js_text

    # Test server-side defense if a 12-digit number is submitted in chat message
    chat_payload = {
        "session_id": "test-aadhaar-pwa",
        "message": "My number is 123456789012, am I eligible?",
    }
    resp = await async_client.post("/api/v1/chat/message", json=chat_payload)
    assert resp.status_code == 200
    data = resp.json()
    # Number must be redacted in answer and session
    assert "123456789012" not in data["answer"]


@pytest.mark.asyncio
async def test_pwa_pan_india_guardrail(async_client: AsyncClient) -> None:
    """Pan-India guardrail: PWA allows evaluating any state domicile without hardcoded locks."""
    res_html = await async_client.get("/")
    assert res_html.status_code == 200

    # Ensure domicile_state is a text input allowing any state, not locked to Manipur
    assert 'id="domicile_state"' in res_html.text
    assert '<input type="text" id="domicile_state"' in res_html.text

    # Non-Manipur profile evaluation executes cleanly
    assam_payload = {
        "domicile_state": "ASSAM",
        "social_category": "GENERAL",
        "annual_family_income_inr": 150000.0,
        "marks_percent": 75.0,
        "course_level": "UNDERGRADUATE",
        "is_displaced": False,
    }
    resp = await async_client.post("/api/v1/eligibility/evaluate", json=assam_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "schemes" in data
