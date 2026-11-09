# SchemeSaathi Production Phase A: Verified AY 2025–26 Data Refresh Report

> **Verdict:** **Ready for reviewer check as a Phase A data refresh**
> **Deciding Reason:** All six pilot schemes have been verified against authentic government guidelines covering Academic Year 2025–2026. The application window status is now deterministically evaluated from statutory open/close dates (`window_status: CLOSED`, `status_label: "Eligible by rules, window closed"`), decoupling it from the static portal operational indicator and preventing closed schemes from being presented as open. All 195 automated tests pass (zero regressions from the 191 baseline, 90% test coverage), and the served PWA initial payload remains strictly within budget at 64,475 bytes (62.96 KB vs 120 KB limit).
>
> *(This phase refreshes the data only — it is not a production launch.)*

---

## 1. Executive Summary

Production Phase A replaces the Academic Year 2024–2025 pilot dataset with verified current-year (AY 2025–2026) statutory scheme data across SchemeSaathi's catalog, deterministic evaluation engine, hybrid retrieval corpus, grounded chat engine, and Progressive Web Application (PWA).

### Critical Problem Solved
In the initial prototype build, schemes with closed application deadlines (e.g. November 30, 2024) were reported to users as `"portal_status": "OPEN"` because `portal_status` was statically populated from portal registration states without cross-referencing statutory application windows against the evaluation date.

### Remediation Delivered in Phase A
1. **Decoupled Window Derivation:** The eligibility engine now derives `window_status` strictly by evaluating `window_open_date <= date.today() <= window_close_date`. If today lies outside the window, `window_status` is guaranteed to be `"CLOSED"` regardless of portal connectivity or legacy flags.
2. **Statutory Status Labelling (`status_label`):** For applicants satisfying all statutory AST criteria whose scheme window is closed, the API reports:
   - `overall_outcome: "ELIGIBLE"` (preserving 3-state Kleene logic and AST rule satisfaction)
   - `window_status: "CLOSED"`
   - `status_label: "Eligible by rules, window closed"`
   - An operational diagnostic clause `"Application Window Status"` (`PASS`) stating the exact closed date.
   For open windows, `status_label: "Eligible, window open"` (`window_status: "OPEN"`).
   For failing profiles, `status_label: "Not eligible"`.
3. **Statutory Guideline Verification:** All 6 pilot schemes have been cross-verified against official Central Ministries (MoTA, MoSJE) and Manipur State Department (DUHE Manipur) governing notifications for AY 2025–2026.
4. **PWA UI Presentation:** Updated the PWA client (`src/static/app.js`) and demo template (`src/templates/demo.html`) to render clear warning badges and human-readable status labels distinguishing rule eligibility from closed application cycles.

---

## 2. Files Modified & Architectural Rationale

| File Path | Component | Architectural Purpose |
|---|---|---|
| `src/modules/catalog/infrastructure/seed_data.py` | Catalog Seed Data | Updated all 6 pilot schemes to `academic_year="2025-2026"`, `portal_status=PortalWindowStatus.CLOSED`, and AY 2025–26 window dates. Added synchronization logic in `seed_pilot_schemes()` so that existing persistent databases are migrated to AY 2025–26 upon startup. |
| `src/modules/eligibility/domain/models.py` | Eligibility Domain Model | Added `window_status: str`, `status_label: str`, `academic_year: str`, and `window_close_date: str | None` to `SchemeEvaluationResult`. |
| `src/modules/eligibility/domain/scheme_evaluator.py` | Deterministic Evaluator | Implemented deterministic window derivation based on `date.today()`, computed human-readable `status_label`, and added the `"Application Window Status"` diagnostic clause. |
| `src/modules/eligibility/application/schemas.py` | Evaluation Schema | Added `window_status`, `status_label`, `academic_year`, and `window_close_date` fields to `SchemeEvaluationResponse`. |
| `src/modules/eligibility/application/evaluator_service.py` | Evaluator Application Service | Propagated window fields from domain result to API response; mapped audit database status to `EvaluationStatus.ELIGIBLE_OFF_CYCLE` when closed. |
| `src/modules/chat/application/schemas.py` | Chat API Schemas | Added `window_status` and `status_label` to `EligibilityItemResult`; set default academic year to `"2025-2026"`. |
| `src/modules/chat/application/chat_service.py` | Chat Application Service | Forwarded `window_status` and `status_label` in `structured_eligibility_items`; updated prose formatting for closed windows. |
| `src/modules/chat/router.py` | Chat Auditor API | Updated checklist fallback academic year to `"2025-2026"` and window close date to `"2025-11-30"`. |
| `src/modules/chat/application/prompt_builder.py` | Prompt Engineering | Updated default academic year fallback in prompt context to `"2025-2026"`. |
| `src/modules/chat/application/citation_checker.py` | Grounding Checker | Updated default academic year fallback in citation resolution to `"2025-2026"`. |
| `src/modules/chat/infrastructure/llm_provider.py` | Test LLM Provider | Updated deterministic test provider chunk and citation fixtures to `"2025-2026"` and `"2025-11-30"`. |
| `src/modules/retrieval/application/corpus_seed_service.py` | Retrieval Corpus | Permitted `"2025-2026"` in corpus header metadata validation; updated statutory disclaimer text to AY 2025–2026. |
| `src/modules/retrieval/application/retrieval_service.py` | Retrieval Service | Updated statutory search response disclaimer to AY 2025–2026. |
| `src/modules/retrieval/infrastructure/repositories.py` | Knowledge Repository | Updated fallback academic year to `"2025-2026"`. |
| `src/static/app.js` | PWA Frontend Logic | Updated UI rendering to display `item.status_label` and `item.window_status` badges (`Closed Window` in high-contrast amber/red); updated Meiteilon/English strings. |
| `src/templates/demo.html` | Demo Template | Updated banner and evaluation cards to display AY 2025–2026 statutory window status. |
| `tests/unit/test_scheme_evaluator.py` | Unit Tests | Added 3 new unit tests verifying window derivation: closed by dates despite portal status open, open when today is inside window, safe default when dates missing. |
| `tests/integration/test_eligibility_api.py` | Integration Tests | Added `test_evaluate_window_status_derivation_open_and_closed` verifying end-to-end API response contract with both open and closed windows. |
| `tests/integration/test_pwa.py` | PWA Integration Tests | Updated PWA assertions to verify AY 2025–2026 and `status_label == "Eligible by rules, window closed"`. |
| `tests/integration/test_retrieval_api.py` | Retrieval Integration Tests | Updated SCH-MN-006 close date expectation to AY 2025–26 (`2025-10-31`). |
| `tests/unit/test_citation_engine.py` | Citation Unit Tests | Updated chunk test fixtures to AY 2025–2026. |

---

## 3. Baseline vs. Final Test Counts

| Milestone / Run | Collected Tests | Passed | Skipped | Failed | Test Coverage | Status |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Sprint 5 Residuals Baseline (Commit `4f93013`)** | 199 | 191 | 8 (Local PG/Redis) | 0 | 90% | **PASSED** (CI `42606719441`) |
| **Phase A Data Refresh (This Delivery)** | **203** | **195** | **8 (Local PG/Redis)** | **0** | **90%** | **PASSED** |

### Net New Substantive Tests (+4 Tests)
1. [`tests/unit/test_scheme_evaluator.py::TestSchemeEvaluatorOutcomes::test_window_status_closed_derived_from_dates_even_if_portal_status_open`](file:///D:/2026/schemesaathi/tests/unit/test_scheme_evaluator.py#L240): Verifies that when a scheme's statutory window closed yesterday but `portal_status` remains `OPEN`, `window_status` evaluates strictly to `"CLOSED"` and `status_label` evaluates to `"Eligible by rules, window closed"`.
2. [`tests/unit/test_scheme_evaluator.py::TestSchemeEvaluatorOutcomes::test_window_status_open_when_today_is_inside_window`](file:///D:/2026/schemesaathi/tests/unit/test_scheme_evaluator.py#L262): Verifies that when `window_open_date <= today <= window_close_date`, `window_status` evaluates strictly to `"OPEN"` and `status_label` evaluates to `"Eligible, window open"`.
3. [`tests/unit/test_scheme_evaluator.py::TestSchemeEvaluatorOutcomes::test_window_status_closed_when_window_dates_are_none`](file:///D:/2026/schemesaathi/tests/unit/test_scheme_evaluator.py#L282): Verifies fail-safe behavior defaulting `window_status` to `"CLOSED"` when dates are missing.
4. [`tests/integration/test_eligibility_api.py::test_evaluate_window_status_derivation_open_and_closed`](file:///D:/2026/schemesaathi/tests/integration/test_eligibility_api.py#L191): Full HTTP integration test registering an actively open scheme version alongside seeded closed schemes, asserting end-to-end API payloads and diagnostic explanations.

### Zero Regression Invariants Verified
- **20 Golden Personas (`tests/integration/test_golden_personas.py`):** 100% deterministic evaluation matching ground-truth outcomes across all 20 personas (0 false positives).
- **Demo Profiles (`tests/integration/test_eligibility_api.py`):**
  - Non-displaced student: Exactly 2 Eligible / 4 Not Eligible / 0 Unknown.
  - Displaced student: Exactly 3 Eligible / 3 Not Eligible / 0 Unknown (`SCH-MN-003` flips cleanly on `is_displaced: True`).
- **Golden Conversations (`tests/integration/test_golden_conversations.py`):** 0 uncited claims, 0 engine contradictions, group-qualified allowance tables verified.
- **PWA Integration (`tests/integration/test_pwa.py`):** All 9 PWA tests pass with zero Aadhaar leakage, offline IndexedDB schema, and payload under budget.

---

## 4. Scheme-by-Scheme Statutory Evidence (AY 2025–2026)

All 6 pilot schemes operate under multi-year statutory guidelines governed by the 15th Finance Commission Cycle (2021–22 to 2025–26) or State Government notifications continued into Academic Year 2025–2026:

### 1. SCH-MN-001: State Merit Scholarship Manipur
- **Issuing Level:** State Sector Scheme
- **Governing Department:** Directorate of University & Higher Education (DUHE), Government of Manipur
- **Official Guideline URL:** `https://scholarships.gov.in/public/schemeGuidelines/Manipur_state_scheme/manipur_Guidelines_3056.pdf`
- **Content SHA256:** `9596807e57debb7b141d18815054363e130a4e7cd454f5bea58598a6ce7ae22c`
- **Guideline Document:** Directorate Circular No. DUHE-3056 / NSP Guidelines, 4 pages.
- **Key Statutory Eligibility Clauses:**
  - Domicile: Permanent Resident of Manipur (`domicile_state == "MANIPUR"`).
  - Academic Merit: Minimum 60.0% marks in qualifying examination.
  - Income Ceiling: No statutory family income ceiling applies.
  - Target Categories: Open to all categories (`GENERAL`, `OBC`, `SC`, `ST`).
- **Academic Year 2025–2026 Window:**
  - Application Window: 2025-07-01 to 2025-11-30
  - Window Status: **CLOSED** (closed on 2025-11-30)
  - Portal Registration: National Scholarship Portal (NSP 2.0)

### 2. SCH-MN-003: Chief Minister’s College Students Rehabilitation Scheme (CMCSRS)
- **Issuing Level:** State Special Welfare Scheme
- **Governing Department:** Directorate of University & Higher Education (DUHE), Government of Manipur
- **Official Guideline URL:** `https://highereducationmanipur.gov.in/chief-ministers-college-students-rehabilitation-scheme-cmcsrs-2023/`
- **Content SHA256:** `8d1949279a2bfbbd5d0ddb5cf079c6fa38aa4d693ffcd8072054ff7fb6839359`
- **Guideline Document:** DUHE Notification No. 1/1-Rehab/2023-HE, 2 pages.
- **Key Statutory Eligibility Clauses:**
  - Domicile: Manipur (`domicile_state == "MANIPUR"`).
  - Special Condition: Must be an internally displaced student affected by ongoing unrest (`is_displaced == True`).
  - Course Level: Undergraduate degree courses in recognized colleges in Manipur.
  - Income Ceiling: No income ceiling.
- **Academic Year 2025–2026 Window:**
  - Application Window: 2025-07-01 to 2026-03-31
  - Window Status: **CLOSED** (pilot cycle closed)
  - Portal Registration: State Higher Education Portal

### 3. SCH-MN-005: Post-Matric Scholarship for ST Students - Manipur
- **Issuing Level:** Centrally Sponsored Scheme (CSS)
- **Governing Ministry:** Ministry of Tribal Affairs (MoTA), Government of India / Department of Tribal Affairs & Hills, Manipur
- **Official Guideline URL:** `https://scholarships.gov.in/public/schemeGuidelines/EDUPostMatricScholarshipPMSforSTstudents.pdf`
- **Content SHA256:** `eb53bc37acc93eccbe811f648e7e741ea05b607db796dc1b759cc8e987256efe`
- **Guideline Document:** Centrally Sponsored Scheme of Post-Matric Scholarship for ST Students, 4 pages.
- **Key Statutory Eligibility Clauses:**
  - Domicile: Manipur.
  - Social Category: Scheduled Tribe (`ST`).
  - Family Income Ceiling: Maximum ₹2,50,000 per annum.
  - Course Level: Post-Matriculation / Higher Secondary, Undergraduate, Postgraduate, Diploma.
  - Academic Marks Cutoff: None.
- **Academic Year 2025–2026 Window:**
  - Application Window: 2025-07-01 to 2025-11-30
  - Window Status: **CLOSED** (closed on 2025-11-30)
  - Portal Registration: NSP 2.0 (requires Aadhaar OTR Face RD)

### 4. SCH-MN-006: Pre-Matric Scholarship for ST Students (Classes IX & X) - Manipur
- **Issuing Level:** Centrally Sponsored Scheme (CSS)
- **Governing Ministry:** Ministry of Tribal Affairs (MoTA), Government of India
- **Official Guideline URL:** `https://scholarships.gov.in/public/schemeGuidelines/guidelines-Pre-matric-ST.pdf`
- **Content SHA256:** `8e35745e6834b1c81ef4539ae2a77f3e8f81e3da07d7f7e915c2cebb42e6a17e`
- **Guideline Document:** MoTA Revised Scheme Guidelines for Pre-Matric Scholarship for ST Students (applicable through 2025–26), 12 pages.
- **Key Statutory Eligibility Clauses:**
  - Domicile: Manipur.
  - Social Category: Scheduled Tribe (`ST`).
  - Family Income Ceiling: Maximum ₹2,50,000 per annum.
  - Course Level: Class 9 or Class 10 (`CLASS_9_10`).
- **Academic Year 2025–2026 Window:**
  - Application Window: 2025-07-01 to 2025-10-31
  - Window Status: **CLOSED** (closed on 2025-10-31)
  - Portal Registration: NSP 2.0

### 5. SCH-MN-007: Post-Matric Scholarship for OBC Students - Manipur
- **Issuing Level:** Centrally Sponsored Scheme (PM-YASASVI)
- **Governing Ministry:** Ministry of Social Justice and Empowerment (MoSJE), Government of India
- **Official Guideline URL:** `https://scholarships.gov.in/public/schemeGuidelines/Centrally%20Sponsored%20Scheme%20of%20Post%20Matric%20Scholarship%20Scheme%20for%20OBC_scheme.pdf`
- **Content SHA256:** `3e7cea65668e2195fceaf83c31ff7380907fc2f559bc85516b71f9cf1297e641`
- **Guideline Document:** PM Young Achievers Scholarship Award Scheme for Vibrant India (PM-YASASVI) Post-Matric OBC Guidelines (covering 2021–22 to 2025–26), 18 pages.
- **Key Statutory Eligibility Clauses:**
  - Domicile: Manipur.
  - Social Category: Other Backward Classes (`OBC`).
  - Family Income Ceiling: Maximum ₹2,50,000 per annum.
  - Course Level: Post-Matriculation, Undergraduate, Postgraduate, Diploma.
- **Academic Year 2025–2026 Window:**
  - Application Window: 2025-07-01 to 2025-11-30
  - Window Status: **CLOSED** (closed on 2025-11-30)
  - Portal Registration: NSP 2.0

### 6. SCH-MN-009: Post-Matric Scholarship for SC Students - Manipur
- **Issuing Level:** Centrally Sponsored Scheme (CSS)
- **Governing Ministry:** Ministry of Social Justice and Empowerment (MoSJE), Government of India
- **Official Guideline URL:** `https://scholarships.gov.in/public/schemeGuidelines/Postmatric_SC.pdf`
- **Content SHA256:** `cf73697b0a39c94541cb834273898687a8bda7fe85ae90e9641e73797c0b0a88`
- **Guideline Document:** Centrally Sponsored Scheme of Post-Matric Scholarship for SC Students (applicable through 2025–26), 18 pages.
- **Key Statutory Eligibility Clauses:**
  - Domicile: Manipur.
  - Social Category: Scheduled Caste (`SC`).
  - Family Income Ceiling: Maximum ₹2,50,000 per annum.
  - Course Level: Post-Matriculation, Undergraduate, Postgraduate, Diploma.
- **Academic Year 2025–2026 Window:**
  - Application Window: 2025-07-01 to 2025-11-30
  - Window Status: **CLOSED** (closed on 2025-11-30)
  - Portal Registration: NSP 2.0

---

## 5. Decoupled Window Status Derivation & API Contracts

### Evaluator Window Derivation Logic
In [`src/modules/eligibility/domain/scheme_evaluator.py`](file:///D:/2026/schemesaathi/src/modules/eligibility/domain/scheme_evaluator.py#L409-L442):
```python
today = date.today()
if window and window.window_open_date is not None and window.window_close_date is not None:
    if window.window_open_date <= today <= window.window_close_date:
        derived_window_status = "OPEN"
    else:
        derived_window_status = "CLOSED"
else:
    derived_window_status = "CLOSED"

# Derive human-readable status_label
if overall_outcome == EvaluationOutcome.ELIGIBLE:
    if derived_window_status == "CLOSED":
        status_label = "Eligible by rules, window closed"
    else:
        status_label = "Eligible, window open"
elif overall_outcome == EvaluationOutcome.NOT_ELIGIBLE:
    status_label = "Not eligible"
else:
    status_label = "Conditionally eligible / information missing"
```

### Worked JSON Example 1: Rule-Eligible Student on Closed Scheme (`SCH-MN-005`)
**Request (`POST /api/v1/eligibility/evaluate`):**
```json
{
  "domicile_state": "MANIPUR",
  "social_category": "ST",
  "annual_family_income_inr": 200000.0,
  "course_level": "UNDERGRADUATE",
  "marks_percent": 65.0,
  "gender": "MALE",
  "is_displaced": false,
  "session_id": "phase-a-evidence-closed"
}
```

**Verbatim Evaluator Response Segment (`SCH-MN-005`):**
```json
{
  "scheme_id": "SCH-MN-005",
  "scheme_title": "Post-Matric Scholarship for ST Students - Manipur",
  "overall_outcome": "ELIGIBLE",
  "diagnostics": [
    {
      "clause_name": "Income Ceiling",
      "outcome": "PASS",
      "explanation_en": "Family income (₹200,000.00) is within statutory ceiling of ₹250,000.00.",
      "missing_fields": []
    },
    {
      "clause_name": "Social Category",
      "outcome": "PASS",
      "explanation_en": "Social category 'ST' matches eligible categories: ['ST'].",
      "missing_fields": []
    },
    {
      "clause_name": "Domicile Restriction",
      "outcome": "PASS",
      "explanation_en": "Domicile state 'MANIPUR' is eligible.",
      "missing_fields": []
    },
    {
      "clause_name": "Academic Cutoff",
      "outcome": "PASS",
      "explanation_en": "No minimum academic marks threshold required.",
      "missing_fields": []
    },
    {
      "clause_name": "Course Level",
      "outcome": "PASS",
      "explanation_en": "Course level 'UNDERGRADUATE' is eligible.",
      "missing_fields": []
    },
    {
      "clause_name": "Statutory AST Rules",
      "outcome": "PASS",
      "explanation_en": "All statutory logic conditions satisfied.",
      "missing_fields": []
    },
    {
      "clause_name": "Application Window Status",
      "outcome": "PASS",
      "explanation_en": "Application window is CLOSED (closed on: 2025-11-30).",
      "missing_fields": []
    }
  ],
  "missing_fields": [],
  "ineligibility_reasons": [],
  "official_source_url": "https://tahmanipur.gov.in",
  "portal_type": "NSP_2_0",
  "portal_status": "CLOSED",
  "window_status": "CLOSED",
  "status_label": "Eligible by rules, window closed",
  "academic_year": "2025-2026",
  "window_close_date": "2025-11-30"
}
```

### Worked JSON Example 2: Ineligible Student on Closed Scheme (`SCH-MN-005`)
**Request:** Income ₹500,000 (exceeds ₹250,000 ceiling), Social category `GENERAL`.
**Verbatim Evaluator Response Segment:**
```json
{
  "scheme_id": "SCH-MN-005",
  "scheme_title": "Post-Matric Scholarship for ST Students - Manipur",
  "overall_outcome": "NOT_ELIGIBLE",
  "diagnostics": [
    {
      "clause_name": "Income Ceiling",
      "outcome": "FAIL",
      "explanation_en": "Annual family income (₹500,000.00) exceeds statutory ceiling of ₹250,000.00.",
      "missing_fields": []
    },
    {
      "clause_name": "Social Category",
      "outcome": "FAIL",
      "explanation_en": "Social category 'GENERAL' is not eligible (Required: ['ST']).",
      "missing_fields": []
    },
    {
      "clause_name": "Application Window Status",
      "outcome": "PASS",
      "explanation_en": "Application window is CLOSED (closed on: 2025-11-30).",
      "missing_fields": []
    }
  ],
  "ineligibility_reasons": [
    "Annual family income (₹500,000.00) exceeds statutory ceiling of ₹250,000.00.",
    "Social category 'GENERAL' is not eligible (Required: ['ST']).",
    "500000.0 exceeds ceiling of 250000.0; 'GENERAL' not found in eligible list ['ST']"
  ],
  "portal_status": "CLOSED",
  "window_status": "CLOSED",
  "status_label": "Not eligible",
  "academic_year": "2025-2026",
  "window_close_date": "2025-11-30"
}
```

### Worked JSON Example 3: Actively Open Scheme (Within Statutory Window)
**Derived Contract:** When `window_open_date <= today <= window_close_date`:
```json
{
  "scheme_id": "SCH-TEST-OPEN",
  "overall_outcome": "ELIGIBLE",
  "window_status": "OPEN",
  "status_label": "Eligible, window open",
  "academic_year": "2025-2026",
  "diagnostics": [
    {
      "clause_name": "Application Window Status",
      "outcome": "PASS",
      "explanation_en": "Application window is OPEN (dates: 2025-11-01 to 2025-12-15)."
    }
  ]
}
```

---

## 6. Post-Matric ST Maintenance Allowance Rate Grounding

In accordance with Sprint 5 fix-3 grounding rules, the Post-Matric ST maintenance allowance rates are verified against the statutory MoTA guideline (`EDUPostMatricScholarshipPMSforSTstudents.pdf`, page 2, section "Maintenance Allowance").

The system strictly enforces group-qualified multi-tier reporting:
- Any statement asserting a single unqualified rate (e.g. *"the allowance is ₹300 per month"*) is rejected by [`CitationEngine.verify_numeric_grounding`](file:///D:/2026/schemesaathi/src/modules/chat/application/citation_checker.py#L270) and fails closed to `STANDARD_REFUSAL_MESSAGE`.
- The complete statutory rate table governing AY 2025–2026 is:

| Course Group | Qualifying Courses | Hostellers (₹/Month) | Day Scholars (₹/Month) |
|:---:|---|:---:|:---:|
| **Group I** | Degree & Post Graduate Professional courses in Medicine, Engineering, Technology, Agriculture, Veterinary, Management, Business Administration | **₹1,200** | **₹550** |
| **Group II** | Other Professional courses leading to Degree/Diploma, Certificate in Pharmacy, Nursing, LLB, BFS, Paramedical | **₹820** | **₹530** |
| **Group III** | General courses not covered under Group I & II (BA, BSc, BCom, etc.) | **₹570** | **₹300** |
| **Group IV** | All Post-Matriculation non-degree courses (Class XI & XII in 10+2 system, ITI, Polytechnic courses) | **₹380** | **₹230** |

All tests covering multi-group tables pass cleanly:
- `test_strengthened_grounding_check_rejects_unqualified_rate_for_multigroup_scheme`
- `test_g2_post_matric_st_allowance_group_qualified_table`
- `test_r1_stub_derives_group_allowance_table_from_chunk_and_fails_when_chunk_changes`

---

## 7. Measured Served PWA Payload Budget

The PWA client served payload was re-measured on a fresh request with empty browser cache against all real served endpoints:

| Asset | Route / Path | Content Type | Size (Bytes) | Size (KB) |
|---|---|---|:---:|:---:|
| **PWA Shell HTML** | `/` | `text/html; charset=utf-8` | 10,012 | 9.78 KB |
| **Web App Manifest** | `/manifest.json` | `application/manifest+json` | 802 | 0.78 KB |
| **Service Worker** | `/sw.js` | `application/javascript` | 4,350 | 4.25 KB |
| **PWA Stylesheet** | `/static/app.css` | `text/css` | 12,515 | 12.22 KB |
| **Application Logic** | `/static/app.js` | `text/javascript` | 31,566 | 30.83 KB |
| **Emblem SVG 192** | `/static/icons/icon-192.svg` | `image/svg+xml` | 619 | 0.60 KB |
| **Emblem PNG 192** | `/static/icons/icon-192.png` | `image/png` | 972 | 0.95 KB |
| **Emblem SVG 512** | `/static/icons/icon-512.svg` | `image/svg+xml` | 636 | 0.62 KB |
| **Emblem PNG 512** | `/static/icons/icon-512.png` | `image/png` | 3,003 | 2.93 KB |
| **TOTAL INITIAL PAYLOAD** | — | — | **64,475** | **62.96 KB** |

### Budget Verdict
- **Hard Budget Limit ($\le 120\text{ KB}$ / 122,880 bytes):** **PASSED** (Headroom: 58,405 bytes / 57.04 KB / 47.5%).
- **M0 Target ($< 115\text{ KB}$ / 117,760 bytes):** **PASSED** (Headroom: 53,285 bytes / 52.04 KB / 45.2%).
- **Largest Single Asset:** `/static/app.js` at **31,566 bytes (30.83 KB)**.
- **Third-Party CDN Assets:** **Zero (0).** Zero external fonts, zero third-party CDNs, zero analytics trackers.

---

## 8. Test Execution & Code Coverage Evidence

### Full Pytest Suite Execution Output
```
============================= test session starts =============================
platform win32 -- Python 3.12.14, pytest-9.2.0, pluggy-1.7.0
rootdir: D:\2026\schemesaathi
configfile: pyproject.toml
plugins: anyio-4.16.0, asyncio-1.4.1.post1, cov-7.1.0
asyncio: mode=Mode.AUTO, debug=False
collected 203 items

tests\integration\test_admin_auth.py .......                             [  3%]
tests\integration\test_document_ingestion_api.py ..........              [  8%]
tests\integration\test_eligibility_api.py ......                         [ 11%]
tests\integration\test_error_redaction.py ....                           [ 13%]
tests\integration\test_golden_conversations.py .................         [ 21%]
tests\integration\test_golden_personas.py .                              [ 22%]
tests\integration\test_health.py ....                                    [ 24%]
tests\integration\test_postgres_pgvector_integration.py sss              [ 25%]
tests\integration\test_postgres_retrieval_integration.py sssss           [ 28%]
tests\integration\test_pwa.py .........                                  [ 32%]
tests\integration\test_request_id_middleware.py ..                       [ 33%]
tests\integration\test_retrieval_api.py ...........                      [ 38%]
tests\integration\test_scheme_catalog_api.py ......                      [ 41%]
tests\integration\test_source_registry_api.py .                          [ 42%]
tests\unit\test_acronym_expansion.py ....                                [ 44%]
tests\unit\test_ast_evaluator.py ...................                     [ 53%]
tests\unit\test_chunking.py ....                                         [ 55%]
tests\unit\test_citation_engine.py ........                              [ 59%]
tests\unit\test_config.py ...                                            [ 61%]
tests\unit\test_database_lifecycle.py ..                                 [ 62%]
tests\unit\test_digital_extractor.py ...                                 [ 63%]
tests\unit\test_document_auditor.py ...                                  [ 65%]
tests\unit\test_embedding_service.py ....                                [ 66%]
tests\unit\test_errors.py ........                                       [ 70%]
tests\unit\test_lifespan.py .                                            [ 71%]
tests\unit\test_logging.py ....                                          [ 73%]
tests\unit\test_models.py ..                                             [ 74%]
tests\unit\test_ocr_extractor.py ..                                      [ 75%]
tests\unit\test_production_fail_safe.py ........                         [ 79%]
tests\unit\test_redis_lifecycle.py ..                                    [ 80%]
tests\unit\test_scheme_evaluator.py ............                         [ 86%]
tests\unit\test_script_router.py ......                                  [ 89%]
tests\unit\test_security_scrubbing.py ....                               [ 91%]
tests\unit\test_sha256_deduplication.py ..........                       [ 96%]
tests\unit\test_state_synchronizer.py ...                                [ 97%]
tests\unit\test_storage_backend.py .....                                 [100%]

=============================== tests coverage ================================
TOTAL                                                         3614    367    90%

=========================== short test summary info ===========================
195 passed, 8 skipped in 297.18s (0:04:57)
```

### Static Analysis & CI Pipeline Verification
- **GitHub Actions Run ID:** [42656965775](https://github.com/mithilesh1627/schemesaathi/actions/runs/42656965775)
- **Commit:** `d26824d` (`feat(phase-a): refresh dataset to AY 2025-26 and enforce statutory window status`)
- **Job 1 (Code Quality):** `completed / success` (Ruff lint, Ruff format check, Mypy strict typing across 91 source files).
- **Job 2 (Automated Unit & Integration Tests):** `completed / success` (Full pytest suite running against live PostgreSQL 16 + pgvector container and Redis cluster; all 203 collected items passed, 90% code coverage).
- **Local Checks:**
  - `ruff check src tests` -> `All checks passed!`
  - `ruff format --check src tests` -> `91 files already formatted`
  - `mypy src tests` -> `Success: no issues found in 91 source files`

---

## 9. Local Verification & Execution Instructions

To reproduce all measurements and test suite results locally:

1. **Activate Virtual Environment & Install Dependencies:**
   ```powershell
   .\.venv\Scripts\Activate.ps1
   pip install -e ".[dev]"
   ```

2. **Run Static Analysis:**
   ```powershell
   ruff check src tests
   ruff format --check src tests
   mypy src tests
   ```

3. **Run Automated Test Suite:**
   ```powershell
   python -m pytest -m "not slow" -v
   ```
   *(Expected: 195 passed, 8 skipped (database integration tests requiring live PostgreSQL/pgvector), 0 failed).*

4. **Verify Payload Budget Measurement:**
   ```powershell
   python -c "
   import asyncio
   from httpx import AsyncClient, ASGITransport
   from src.main import app

   async def check():
       routes = ['/', '/manifest.json', '/sw.js', '/static/app.css', '/static/app.js',
                 '/static/icons/icon-192.svg', '/static/icons/icon-192.png',
                 '/static/icons/icon-512.svg', '/static/icons/icon-512.png']
       async with AsyncClient(transport=ASGITransport(app=app), base_url='http://testserver') as client:
           total = sum([len((await client.get(r)).content) for r in routes])
           print(f'Total Served Payload: {total} bytes ({total/1024:.2f} KB)')
           assert total <= 122880, 'Payload exceeded 120 KB hard limit'
   asyncio.run(check())
   "
   ```

5. **Start Local Development Server:**
   ```powershell
   uvicorn src.main:app --host 127.0.0.1 --port 8000
   ```
   Access the PWA shell at `http://127.0.0.1:8000/` or the statutory demo at `http://127.0.0.1:8000/demo`.

---

## 10. Known Limitations & Next Steps

1. **Phase A Scope Boundary:** Phase A strictly encompasses statutory dataset refresh, window status decoupling, and contract alignment. It does **not** constitute a public launch or full production sign-off.
2. **PostgreSQL 16 + pgvector Integration Tests:** The 8 integration tests requiring an active live PostgreSQL instance and Redis cluster are cleanly skipped in local environments without Docker services running, and pass in full CI runner environments with services configured.
3. **Field Pilot Protocol:** The field pilot protocol prepared in `docs/pilot/field_pilot_protocol.md` remains documented and ready for execution, but has **not** been run (in line with reviewer guidance).
4. **Subsequent Hardening (Production Phase B & C):**
   - Phase B: Production deployment configuration, security headers (CSP, HSTS, X-Content-Type-Options), rate-limiting persistence in Redis, and structured error alerting.
   - Phase C: Load testing on high-concurrency synthetic profiles and automated daily portal window scraping probes.

---

### Final Recommendation
**Ready for reviewer check as a Phase A data refresh**
*(This phase refreshes the data only — it is not a production launch.)*
