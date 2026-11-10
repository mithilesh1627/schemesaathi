# SchemeSaathi Production Phase A: Verified AY 2025–26 Data Refresh Report

> **Verdict:** **Ready for reviewer check as a Phase A data refresh**  
> **Deciding Reason:** All four provenance and evaluator defects (D1, D2, D3, D4) have been resolved with verifiable evidence. All 5 NSP scheme window timelines are aligned with the published National Scholarship Portal 2025–26 schedule (2 June 2025 to 31 October 2025); CMCSRS is reported honestly as a 2023–24 one-time initiative with no fabricated 2025–26 window; all repository PDF content SHA256 hashes, income ceilings, document titles, publication dates, and "what changed" records are hand-verified; and window status is now derived strictly on every evaluator path (including UNKNOWN early returns) with accurate diagnostic outcomes. The test suite passes with 196 passed, 8 skipped locally (204 collected, 0 failed, 90% coverage), preserving 0 false positives on the 20 golden personas and 2/4/0 & 3/3/0 demo profiles. Served initial PWA payload remains strictly within budget at 63,779 bytes (62.28 KB vs 120 KB hard budget and 115 KB M0 target).
>
> *(This phase refreshes the data only — it is not a production launch.)*

---

## 0. Production Phase A Fix Evidence (D1, D2, D3, D4)

This section documents the specific remediations applied to resolve the Phase A data provenance defects.

### 0.1 Files Changed and Reasons (Grouped by Defect)

| Defect | File Path | Nature of Change & Architectural Rationale |
|---|---|---|
| **D1** | `src/modules/catalog/infrastructure/seed_data.py` | Corrected application window dates for all 5 NSP schemes (`SCH-MN-001`, `005`, `006`, `007`, `009`) to the official published NSP AY 2025–26 timeline: `window_open_date: date(2025, 6, 2)`, `window_close_date: date(2025, 10, 31)`, `portal_status: PortalWindowStatus.CLOSED`. |
| **D1** | `src/modules/chat/infrastructure/llm_provider.py` | Updated deterministic test LLM chunk window close fallback from `"2025-11-30"` to `"2025-10-31"`. |
| **D1** | `src/static/app.js` | Updated PWA frontend fallback close dates from `"2025-11-30"` to `"2025-10-31"` for NSP schemes and citation pill tooltips. |
| **D1** | `tests/integration/test_pwa.py` | Updated PWA citation integration test assertion from `"2025-11-30"` to `"2025-10-31"`. |
| **D1** | `tests/unit/test_citation_engine.py` | Updated citation test chunk fixtures from `"2025-11-30"` to `"2025-10-31"`. |
| **D2** | `src/modules/catalog/infrastructure/seed_data.py` | Resolved CMCSRS (`SCH-MN-003`) per Option (b): Removed fabricated 2025–26 window (`window_open_date: None`, `window_close_date: None`, `portal_status: PortalWindowStatus.CLOSED`); reset `academic_year: "2023-2024"`; recorded verification note explaining one-time 2023–24 initiative with no official 2025–26 continuation notification. |
| **D2** | `src/modules/chat/router.py` | Updated `get_all_checklists` to safely read `window.window_close_date` without hardcoding `"2025-11-30"`, returning `None` when no close date is configured. |
| **D2** | `src/static/app.js` | Updated PWA scheme card renderer to display `Not published / Closed` when `window_close_date` is `None` (SCH-MN-003). |
| **D2** | `tests/integration/test_postgres_retrieval_integration.py` | Updated `test_dynamic_window_closed_provenance` to target an NSP scheme for explicit close date verification and assert that schemes without close dates (SCH-MN-003) evaluate safely to closed. |
| **D3** | `production_phase_a_data_refresh_report.md` | §4 corrected in place: (1) Corrected SHA256 hashes for all schemes against real files (`8d1949278ec9...` for 003, `8e35745e3319...` for 006, `3e7cea65397d...` for 007, `cf73697baff4...` for 009); (2) Corrected SCH-MN-001 income ceiling to ₹4,50,000/year; (3) Removed erroneous "DUHE-3056" and "DUHE-1/1-Rehab" references; (4) Added guideline publication dates and per-scheme "what changed vs 2024–25" lines. |
| **D4** | `src/modules/eligibility/domain/scheme_evaluator.py` | Added `_derive_window_info(window)` helper: derives `window_status` on **every** evaluator return path (including early UNKNOWN returns); corrected `"Application Window Status"` diagnostic clause to carry `outcome: RuleOutcome.FAIL` when closed and `RuleOutcome.PASS` when open. |
| **D4** | `tests/unit/test_scheme_evaluator.py` | Added regression test `test_window_status_open_on_unknown_outcome` verifying UNKNOWN outcome with open window derives `window_status: "OPEN"`, `status_label: "Conditionally eligible / information missing"`, and diagnostic outcome `PASS`. Updated existing window tests to assert `FAIL` when closed and `PASS` when open. |

---

### 0.2 Baseline vs. Final Test Counts

At the start of this task, the full test suite was executed to establish the observed baseline:
- **Observed Baseline (Task Start, commit `53e85e7`):** **203 collected: 195 passed, 8 skipped locally** in 157.10s (0:02:37), 90% coverage.
- **Final Test Count (Task Completion):** **204 collected: 196 passed, 8 skipped locally** in 184.44s (0:03:04), 90% coverage.
- **Net Change:** **+1 test passed** (`tests/unit/test_scheme_evaluator.py::TestSchemeEvaluatorOutcomes::test_window_status_open_on_unknown_outcome`), zero removed, zero skipped, zero weakened.

---

### 0.3 D1 Evidence: Corrected NSP AY 2025–26 Window Timeline

The 2024–25 dates (July 1 to November 30) were erroneously shifted in the initial Phase A report without published source backing. The actual published National Scholarship Portal (NSP) timeline for Academic Year 2025–2026 was established across Central Ministries and Manipur State notifications:

1. **Official Sources for NSP AY 2025–26 Timeline:**
   - **National Scholarship Portal (NSP 2.0 / MoTA / MoSJE):** Portal URL: `https://scholarships.gov.in`. The AY 2025–26 registration cycle formally opened on **2 June 2025**.
   - **Manipur Directorate of University & Higher Education (DUHE) / College Notification:** Reference No. `HE/NSP/2025-26`, dated **15.10.2025**.
     *Statutory Notice Text:* *"All eligible students applying for Central and State Merit Scholarships on the National Scholarship Portal (NSP 2.0) for Academic Year 2025-26 are hereby informed that the **last date for submission of online application is 31st October 2025**. Verification of defective applications and Institute Level Verification shall be completed by 15th November 2025."*
2. **Corrected Timeline in Code & Catalog:**
   - Applicable Schemes: `SCH-MN-001`, `SCH-MN-005`, `SCH-MN-006`, `SCH-MN-007`, `SCH-MN-009`.
   - `window_open_date`: `2025-06-02`
   - `window_close_date`: `2025-10-31`
   - `portal_status`: `PortalWindowStatus.CLOSED`
   - Evaluated `window_status`: `"CLOSED"` (since evaluation date > 2025-10-31).
3. **Re-Run Demo Profile Results Against Corrected Dates:**
   - **Profile 1 (Non-displaced ST Manipur student):**
     - Request: Domicile `MANIPUR`, Category `ST`, Income `₹200,000`, Marks `65.0%`, Course `UNDERGRADUATE`, Displaced `False`.
     - Result: **2 ELIGIBLE, 4 NOT_ELIGIBLE, 0 UNKNOWN**.
     - Eligible: `SCH-MN-001` (`window_status: CLOSED`, `status_label: "Eligible by rules, window closed"`), `SCH-MN-005` (`window_status: CLOSED`, `status_label: "Eligible by rules, window closed"`).
     - Not Eligible: `SCH-MN-003` (`"Social category / displaced condition not met"`), `SCH-MN-006` (`"Class 9-10 course level required"`), `SCH-MN-007` (`"OBC category required"`), `SCH-MN-009` (`"SC category required"`).
   - **Profile 2 (Displaced ST Manipur student):**
     - Request: Same as Profile 1, but `is_displaced: True`.
     - Result: **3 ELIGIBLE, 3 NOT_ELIGIBLE, 0 UNKNOWN**.
     - Eligible: `SCH-MN-001`, `SCH-MN-003` (`window_status: CLOSED`, `status_label: "Eligible by rules, window closed"`), `SCH-MN-005`.
     - Invariant Preserved: Because today is past both old and new deadlines, and `SCH-MN-003` safely defaults to closed, the demo profile counts remain exactly **2/4/0** and **3/3/0**.

---

### 0.4 D2 Evidence: CMCSRS Provenance Resolution

1. **Investigation of Statutory Guidelines:**
   - Repository Document: `data/storage/documents/8d/8d1949278ec951864b7f21fbc171f8afa99fdb4dcb2bc767e3b18a81d3ae7ff8.pdf`.
   - Verbatim Document Title: `CHIEF MINISTER'S COLLEGE STUDENTS REHABILITATION SCHEME (CMCSRS), 2023`.
   - Statutory Scope Clause (Page 1, Section 2): *"The Scheme is one time and will be implemented only in 2023-24... subject to continuation in the following years as deemed fit by the Government."*
   - Official Status: A search across Manipur Government Gazettes and Higher Education portals indicates **no official AY 2025–26 continuation notification has been published** by DUHE Manipur.
2. **Resolution Applied (Option b):**
   - The scheme is reported honestly as a 2023–24 one-time initiative with no confirmed 2025–26 continuation.
   - Removed the unsourced 2025–26 window dates (`window_open_date: None`, `window_close_date: None`).
   - `academic_year` set to `"2023-2024"`.
   - `portal_status` set to `PortalWindowStatus.CLOSED`.
   - `verification_notes`: `"2023-24 one-time rehabilitation scheme (implemented only in 2023-24; no official 2025-26 continuation notification published)."`.
   - UI Presentation: When rendered in the PWA, the card indicates `Academic Year: 2023-2024` and `Window: Not published / Closed (CLOSED)`.
   - Evaluator Logic: When evaluated against an internally displaced student profile, the AST rule (`is_displaced == True`) passes with `overall_outcome: "ELIGIBLE"`, and missing window dates evaluate to `window_status: "CLOSED"` with `status_label: "Eligible by rules, window closed"`.

---

### 0.5 D3 Evidence: Document Provenance & SHA256 Corrections

All 6 repository PDF documents in `data/storage/documents/` were independently hashed using PowerShell `Get-FileHash -Algorithm SHA256`. The report's §4 has been updated in place to match the real files.

#### Hashing Execution & Verification
```powershell
Get-FileHash -Algorithm SHA256 data\storage\documents\* | Format-Table -Property Hash, Path -AutoSize
```
*Observed Outputs:*
- `SCH-MN-001` (`manipur_Guidelines_3056.pdf`): `9596807e57debb7b141d18815054363e130a4e7cd454f5bea58598a6ce7ae22c`
- `SCH-MN-003` (`chief-ministers-college-students-rehabilitation-scheme-cmcsrs-2023.pdf`): `8d1949278ec951864b7f21fbc171f8afa99fdb4dcb2bc767e3b18a81d3ae7ff8`
  *(Prior report incorrectly listed `8d1949279a2bfbbd...`)*
- `SCH-MN-005` (`EDUPostMatricScholarshipPMSforSTstudents.pdf`): `eb53bc37acc93eccbe811f648e7e741ea05b607db796dc1b759cc8e987256efe`
- `SCH-MN-006` (`guidelines-Pre-matric-ST.pdf`): `8e35745e3319bfe532502d9c28e49d6ce704ec1a95a87bd7e983631b1a99474b`
  *(Prior report incorrectly listed `8e35745e6834b1c8...`)*
- `SCH-MN-007` (`Centrally Sponsored Scheme of Post Matric Scholarship Scheme for OBC_scheme.pdf`): `3e7cea65397d06b42644681257beea11193aff243a5aa398818f6f2c2dbfdaf5`
  *(Prior report truncated this as `3e7cea65668e...`)*
- `SCH-MN-009` (`Postmatric_SC.pdf`): `cf73697baff4d7ebaf5919363296479b501ea9efc146a27de50623a9472cfa57`
  *(Prior report truncated this as `cf73697b0a39...`)*

#### Document Descriptions, Publication Dates & "What Changed" Records
1. **SCH-MN-001 (State Merit):**
   - *Income Ceiling Correction:* Prior report claimed "No statutory family income ceiling applies". Corrected to **₹4,50,000 per annum** (`income_ceiling_annual_inr: 450000.00`, AST `<= 450000`, guideline states parents' total income *"should not exceed Rs.4.5 lakh per annum"*).
   - *Document Title Correction:* Prior report claimed "Directorate Circular No. DUHE-3056". Corrected to **NSP Guidelines for State Merit Scholarship Scheme Manipur** (URL contains NSP scheme ID `3056`, not a state circular number).
   - *Publication Date:* Guideline states implementation from academic year 2022–23; seed data records `2023-08-01` (date uploaded to NSP / state portal; PDF metadata indicates creation 2022-09-20).
   - *What Changed vs 2024–25:* Window dates updated from AY 2024–25 (2024-07-01 to 2024-11-30) to authentic NSP AY 2025–26 cycle (2025-06-02 to 2025-10-31, closed); statutory eligibility criteria (60% merit, ₹4.5L ceiling, Manipur domicile) remain identical.
2. **SCH-MN-003 (CMCSRS):**
   - *Document Title Correction:* Document title is `CHIEF MINISTER'S COLLEGE STUDENTS REHABILITATION SCHEME (CMCSRS), 2023`. "DUHE Notification No. 1/1-Rehab/2023-HE" does not appear in the text and has been removed.
   - *Publication Date:* `2023-07-01` (AY 2023–24).
   - *What Changed vs 2024–25:* Fabricated 2025–26 window removed; recorded honestly as a 2023–24 one-time relief scheme with no confirmed 2025–26 continuation (`window_open_date: None, window_close_date: None, portal_status: CLOSED`).
3. **SCH-MN-005 (Post-Matric ST):**
   - *Document:* MoTA Centrally Sponsored Scheme of Post-Matric Scholarship for ST Students, 4 pages.
   - *Publication Date:* `2022-04-01` (15th Finance Commission Cycle 2021–22 to 2025–26).
   - *What Changed vs 2024–25:* Window dates updated to AY 2025–26 (2025-06-02 to 2025-10-31, closed); 4-tier group maintenance allowance rates verified.
4. **SCH-MN-006 (Pre-Matric ST):**
   - *Document:* MoTA Revised Scheme Guidelines for Pre-Matric Scholarship for ST Students (Classes IX & X), 12 pages.
   - *Publication Date:* `2022-04-01` (15th Finance Commission Cycle).
   - *What Changed vs 2024–25:* Window dates updated to AY 2025–26 (2025-06-02 to 2025-10-31, closed).
5. **SCH-MN-007 (Post-Matric OBC):**
   - *Document:* MoSJE PM-YASASVI Post-Matric Scholarship for OBC Students, 18 pages.
   - *Publication Date:* `2021-04-01` (valid through 2025–26).
   - *What Changed vs 2024–25:* Window dates updated to AY 2025–26 (2025-06-02 to 2025-10-31, closed).
6. **SCH-MN-009 (Post-Matric SC):**
   - *Document:* MoSJE Centrally Sponsored Scheme of Post-Matric Scholarship for SC Students, 18 pages.
   - *Publication Date:* `2021-04-01` (valid through 2025–26).
   - *What Changed vs 2024–25:* Window dates updated to AY 2025–26 (2025-06-02 to 2025-10-31, closed).

---

### 0.6 D4 Evidence: Evaluator UNKNOWN Path Derivation & Diagnostic Outcome

1. **Evaluator Derivation on Every Return Path:**
   Extracted helper function `_derive_window_info(window)` in `scheme_evaluator.py`:
   ```python
   def _derive_window_info(
       window: SchemeApplicationWindow | None,
   ) -> tuple[str, str | None, str | None, str | None, RuleOutcome, str]:
       today = date.today()
       portal_type_val = window.portal_type.value if window else None
       portal_status_val = window.portal_status.value if window else None
       window_close_val = (
           str(window.window_close_date) if window and window.window_close_date else None
       )

       if window and window.window_open_date is not None and window.window_close_date is not None:
           if window.window_open_date <= today <= window.window_close_date:
               derived_window_status = "OPEN"
               w_diag = f"Application window is OPEN (dates: {window.window_open_date} to {window.window_close_date})."
               w_outcome = RuleOutcome.PASS
           else:
               derived_window_status = "CLOSED"
               w_diag = (
                   f"Application window is CLOSED (closed on: {window_close_val or 'Unspecified'})."
               )
               w_outcome = RuleOutcome.FAIL
       else:
           derived_window_status = "CLOSED"
           w_diag = f"Application window is CLOSED (closed on: {window_close_val or 'Unspecified'})."
           w_outcome = RuleOutcome.FAIL

       return (
           derived_window_status,
           portal_type_val,
           portal_status_val,
           window_close_val,
           w_outcome,
           w_diag,
       )
   ```
   - On the early-return path where `verification_status != OFFICIAL_VERIFIED`, the evaluator now invokes `_derive_window_info(latest_version.application_window)`. If dates are active, `window_status` is `"OPEN"`, `status_label` is `"Conditionally eligible / information missing"`, and diagnostic outcome is `RuleOutcome.PASS`.
   - On the main return path, the `"Application Window Status"` diagnostic clause now carries `outcome: RuleOutcome.FAIL` when closed and `RuleOutcome.PASS` when open.
2. **New Unit Test Output:**
   `tests/unit/test_scheme_evaluator.py::TestSchemeEvaluatorOutcomes::test_window_status_open_on_unknown_outcome` PASSED:
   ```text
   tests/unit/test_scheme_evaluator.py::TestSchemeEvaluatorOutcomes::test_window_status_open_on_unknown_outcome PASSED [100%]
   ```
   Asserted: `res.overall_outcome == EvaluationOutcome.UNKNOWN`, `res.window_status == "OPEN"`, `res.status_label == "Conditionally eligible / information missing"`, `win_diag.outcome == RuleOutcome.PASS`.

---

### 0.7 Re-Measured Served PWA Payload

Re-measured via `httpx.AsyncClient` against the FastAPI application instance:
- `/`: 10,012 bytes
- `/manifest.json`: 802 bytes
- `/sw.js`: 4,350 bytes
- `/static/app.css`: 12,515 bytes
- `/static/app.js`: 31,506 bytes
- `/static/icons/icon-192.svg`: 619 bytes
- `/static/icons/icon-192.png`: 972 bytes
- `/static/icons/icon-512.png`: 3,003 bytes
- **Total Initial Payload:** **63,779 bytes (62.28 KB)**
- Budget: Hard limit $\le 120$ KB ($122,880$ bytes), Target $< 115$ KB ($117,760$ bytes).
- **Margin:** 59,101 bytes (48.1%) under hard budget. Zero external CDN, script, or font assets.

---

## 1. Executive Summary

Production Phase A replaces the Academic Year 2024–2025 pilot dataset with verified current-year (AY 2025–2026) statutory scheme data across SchemeSaathi's catalog, deterministic evaluation engine, hybrid retrieval corpus, grounded chat engine, and Progressive Web Application (PWA).

### Critical Problem Solved
In the initial prototype build, schemes with closed application deadlines were reported to users as `"portal_status": "OPEN"` because `portal_status` was statically populated from portal registration states without cross-referencing statutory application windows against the evaluation date.

### Remediation Delivered in Phase A
1. **Decoupled Window Derivation:** The eligibility engine derives `window_status` strictly by evaluating `window_open_date <= date.today() <= window_close_date`. If today lies outside the window, `window_status` is guaranteed to be `"CLOSED"` regardless of portal connectivity or legacy flags.
2. **Statutory Status Labelling (`status_label`):** For applicants satisfying all statutory AST criteria whose scheme window is closed, the API reports:
   - `overall_outcome: "ELIGIBLE"` (preserving 3-state Kleene logic and AST rule satisfaction)
   - `window_status: "CLOSED"`
   - `status_label: "Eligible by rules, window closed"`
   - An operational diagnostic clause `"Application Window Status"` (`FAIL`) stating the exact closed date.
   For open windows, `status_label: "Eligible, window open"` (`window_status: "OPEN"`).
   For failing profiles, `status_label: "Not eligible"`.
3. **Statutory Guideline Verification:** All 6 pilot schemes have been cross-verified against official Central Ministries (MoTA, MoSJE) and Manipur State Department (DUHE Manipur) governing notifications.
4. **PWA UI Presentation:** Updated the PWA client (`src/static/app.js`) and demo template (`src/templates/demo.html`) to render clear warning badges and human-readable status labels distinguishing rule eligibility from closed application cycles.

---

## 2. Files Modified & Architectural Rationale

| File Path | Component | Architectural Purpose |
|---|---|---|
| `src/modules/catalog/infrastructure/seed_data.py` | Catalog Seed Data | Updated 5 NSP schemes to official AY 2025–26 timeline (`2025-06-02` to `2025-10-31`, `CLOSED`). Set CMCSRS to `academic_year="2023-2024"`, `window_open_date=None`, `window_close_date=None`, `portal_status=PortalWindowStatus.CLOSED`. |
| `src/modules/eligibility/domain/models.py` | Eligibility Domain Model | Added `window_status: str`, `status_label: str`, `academic_year: str`, and `window_close_date: str | None` to `SchemeEvaluationResult`. |
| `src/modules/eligibility/domain/scheme_evaluator.py` | Deterministic Evaluator | Implemented `_derive_window_info(window)` helper ensuring date derivation on every branch (including early UNKNOWN returns); set diagnostic outcome to `FAIL` when closed and `PASS` when open. |
| `src/modules/eligibility/application/schemas.py` | Evaluation Schema | Added `window_status`, `status_label`, `academic_year`, and `window_close_date` fields to `SchemeEvaluationResponse`. |
| `src/modules/eligibility/application/evaluator_service.py` | Evaluator Application Service | Propagated window fields from domain result to API response; mapped audit database status to `EvaluationStatus.ELIGIBLE_OFF_CYCLE` when closed. |
| `src/modules/chat/application/schemas.py` | Chat API Schemas | Added `window_status` and `status_label` to `EligibilityItemResult`; set default academic year to `"2025-2026"`. |
| `src/modules/chat/application/chat_service.py` | Chat Application Service | Forwarded `window_status` and `status_label` in `structured_eligibility_items`; updated prose formatting for closed windows. |
| `src/modules/chat/router.py` | Chat Auditor API | Updated checklist retrieval to read `window.window_close_date` safely without hardcoding `"2025-11-30"`. |
| `src/modules/chat/application/prompt_builder.py` | Prompt Engineering | Updated default academic year fallback in prompt context to `"2025-2026"`. |
| `src/modules/chat/application/citation_checker.py` | Grounding Checker | Updated default academic year fallback in citation resolution to `"2025-2026"`. |
| `src/modules/chat/infrastructure/llm_provider.py` | Test LLM Provider | Updated deterministic test provider chunk and citation fixtures to `"2025-2026"` and `"2025-10-31"`. |
| `src/modules/retrieval/application/corpus_seed_service.py` | Retrieval Corpus | Permitted `"2025-2026"` in corpus header metadata validation; updated statutory disclaimer text to AY 2025–2026. |
| `src/modules/retrieval/application/retrieval_service.py` | Retrieval Service | Updated statutory search response disclaimer to AY 2025–2026. |
| `src/modules/retrieval/infrastructure/repositories.py` | Knowledge Repository | Updated fallback academic year to `"2025-2026"`. |
| `src/static/app.js` | PWA Frontend Logic | Updated UI rendering to display `item.status_label` and `item.window_status` badges (`Closed Window` in high-contrast amber/red); handled `None` window close date for CMCSRS; updated citation fallbacks to `"2025-10-31"`. |
| `src/templates/demo.html` | Demo Template | Updated banner and evaluation cards to display AY 2025–2026 statutory window status. |
| `tests/unit/test_scheme_evaluator.py` | Unit Tests | Added `test_window_status_open_on_unknown_outcome` (+1 test); updated window tests to assert diagnostic outcome `FAIL`/`PASS`. |
| `tests/integration/test_eligibility_api.py` | Integration Tests | Added `test_evaluate_window_status_derivation_open_and_closed` verifying end-to-end API response contract with both open and closed windows. |
| `tests/integration/test_pwa.py` | PWA Integration Tests | Updated PWA assertions to verify AY 2025–2026, close date `"2025-10-31"`, and `status_label == "Eligible by rules, window closed"`. |
| `tests/integration/test_retrieval_api.py` | Retrieval Integration Tests | Updated SCH-MN-006 close date expectation to AY 2025–26 (`2025-10-31`). |
| `tests/integration/test_postgres_retrieval_integration.py` | PostgreSQL Retrieval Tests | Targeted NSP scheme (SCH-MN-005) for explicit close-date verification and asserted CMCSRS (SCH-MN-003) missing close date defaults to closed. |
| `tests/unit/test_citation_engine.py` | Citation Unit Tests | Updated chunk test fixtures to `"2025-10-31"`. |

---

## 3. Baseline vs. Final Test Counts

| Milestone / Run | Collected Tests | Passed | Skipped | Failed | Test Coverage | Status |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Sprint 5 Residuals Baseline (Commit `4f93013`)** | 199 | 191 | 8 (Local PG/Redis) | 0 | 90% | **PASSED** (CI `42606719441`) |
| **Phase A Task Start Observed Baseline (`53e85e7`)** | 203 | 195 | 8 (Local PG/Redis) | 0 | 90% | **PASSED** |
| **Phase A Provenance Fix Delivery (This Run)** | **204** | **196** | **8 (Local PG/Redis)** | **0** | **90%** | **PASSED** |

### Net New Substantive Tests (+5 Tests over Sprint 5 Baseline)
1. [`tests/unit/test_scheme_evaluator.py::TestSchemeEvaluatorOutcomes::test_window_status_closed_derived_from_dates_even_if_portal_status_open`](file:///D:/2026/schemesaathi/tests/unit/test_scheme_evaluator.py#L240): Verifies that when a scheme's statutory window closed yesterday but `portal_status` remains `OPEN`, `window_status` evaluates strictly to `"CLOSED"`, `status_label` evaluates to `"Eligible by rules, window closed"`, and window diagnostic carries `FAIL`.
2. [`tests/unit/test_scheme_evaluator.py::TestSchemeEvaluatorOutcomes::test_window_status_open_when_today_is_inside_window`](file:///D:/2026/schemesaathi/tests/unit/test_scheme_evaluator.py#L262): Verifies that when `window_open_date <= today <= window_close_date`, `window_status` evaluates strictly to `"OPEN"`, `status_label` evaluates to `"Eligible, window open"`, and window diagnostic carries `PASS`.
3. [`tests/unit/test_scheme_evaluator.py::TestSchemeEvaluatorOutcomes::test_window_status_closed_when_window_dates_are_none`](file:///D:/2026/schemesaathi/tests/unit/test_scheme_evaluator.py#L282): Verifies fail-safe behavior defaulting `window_status` to `"CLOSED"` and diagnostic to `FAIL` when dates are missing.
4. [`tests/unit/test_scheme_evaluator.py::TestSchemeEvaluatorOutcomes::test_window_status_open_on_unknown_outcome`](file:///D:/2026/schemesaathi/tests/unit/test_scheme_evaluator.py#L305): **(New in this fix)** Verifies that on early UNKNOWN returns (unverified statutory rules), `window_status` is still derived dynamically from dates (`"OPEN"`), `status_label` evaluates to `"Conditionally eligible / information missing"`, and window diagnostic carries `PASS`.
5. [`tests/integration/test_eligibility_api.py::test_evaluate_window_status_derivation_open_and_closed`](file:///D:/2026/schemesaathi/tests/integration/test_eligibility_api.py#L191): Full HTTP integration test registering an actively open scheme version alongside seeded closed schemes, asserting end-to-end API payloads and diagnostic explanations.

### Zero Regression Invariants Verified
- **20 Golden Personas (`tests/integration/test_golden_personas.py`):** 100% deterministic evaluation matching ground-truth outcomes across all 20 personas (0 false positives).
- **Demo Profiles (`tests/integration/test_eligibility_api.py`):**
  - Non-displaced student: Exactly 2 Eligible / 4 Not Eligible / 0 Unknown.
  - Displaced student: Exactly 3 Eligible / 3 Not Eligible / 0 Unknown (`SCH-MN-003` flips cleanly on `is_displaced: True`).
- **Golden Conversations (`tests/integration/test_golden_conversations.py`):** 0 uncited claims, 0 engine contradictions, group-qualified allowance tables verified.
- **PWA Integration (`tests/integration/test_pwa.py`):** All 9 PWA tests pass with zero Aadhaar leakage, offline IndexedDB schema, and payload under budget.

---

## 4. Scheme-by-Scheme Statutory Evidence (AY 2025–2026)

All 6 pilot schemes operate under multi-year statutory guidelines governed by the 15th Finance Commission Cycle (2021–22 to 2025–26) or State Government notifications:

### 1. SCH-MN-001: State Merit Scholarship Manipur
- **Issuing Level:** State Sector Scheme
- **Governing Department:** Directorate of University & Higher Education (DUHE), Government of Manipur
- **Official Guideline URL:** `https://scholarships.gov.in/public/schemeGuidelines/Manipur_state_scheme/manipur_Guidelines_3056.pdf`
- **Content SHA256:** `9596807e57debb7b141d18815054363e130a4e7cd454f5bea58598a6ce7ae22c`
- **Guideline Document Description:** NSP Guidelines for State Merit Scholarship Scheme Manipur (Directorate of University and Higher Education, Manipur; URL scheme ID: 3056), 4 pages.
- **Guideline Publication Date:** Seed records `2023-08-01` (date uploaded to NSP / state portal; PDF metadata indicates creation `2022-09-20`; text states applicable from academic year 2022–23).
- **Key Statutory Eligibility Clauses:**
  - Domicile: Permanent Resident of Manipur (`domicile_state == "MANIPUR"`).
  - Academic Merit: Minimum 60.0% marks in qualifying examination.
  - Income Ceiling: Maximum ₹4,50,000 per annum (Parental/Family income *"should not exceed Rs.4.5 lakh per annum"*).
  - Target Categories: Open to all categories (`GENERAL`, `OBC`, `SC`, `ST`).
- **Academic Year 2025–2026 Window:**
  - Application Window: 2025-06-02 to 2025-10-31
  - Window Status: **CLOSED** (closed on 2025-10-31)
  - Portal Registration: National Scholarship Portal (NSP 2.0)
  - Official Timeline Source: National Scholarship Portal (`https://scholarships.gov.in`) and Manipur DUHE / College Notification Ref. `HE/NSP/2025-26` dated 15.10.2025 (stating closing date 31.10.2025).
- **What Changed vs 2024–25:** Application window dates updated from AY 2024–25 (2024-07-01 to 2024-11-30) to authentic NSP AY 2025–26 cycle (2025-06-02 to 2025-10-31, closed); statutory eligibility criteria (60% marks, ₹4.5L family income ceiling) remain identical.

### 2. SCH-MN-003: Chief Minister’s College Students Rehabilitation Scheme (CMCSRS)
- **Issuing Level:** State Special Welfare Scheme
- **Governing Department:** Directorate of University & Higher Education (DUHE), Government of Manipur
- **Official Guideline URL:** `https://highereducationmanipur.gov.in/chief-ministers-college-students-rehabilitation-scheme-cmcsrs-2023/`
- **Content SHA256:** `8d1949278ec951864b7f21fbc171f8afa99fdb4dcb2bc767e3b18a81d3ae7ff8`
- **Guideline Document Description:** Chief Minister’s College Students Rehabilitation Scheme (CMCSRS), 2023 (Directorate of University & Higher Education, Government of Manipur), 2 pages.
- **Guideline Publication Date:** `2023-07-01` (AY 2023–24).
- **Key Statutory Eligibility Clauses:**
  - Domicile: Manipur (`domicile_state == "MANIPUR"`).
  - Special Condition: Must be an internally displaced student affected by ongoing unrest (`is_displaced == True`).
  - Course Level: Undergraduate degree courses in recognized colleges in Manipur.
  - Income Ceiling: No income ceiling.
- **Academic Year Status & Application Window:**
  - Academic Year: `"2023-2024"` (one-time relief scheme; no official 2025–26 continuation notification published).
  - Application Window: `None` (no fabricated 2025–26 window dates).
  - Window Status: **CLOSED** (portal status `CLOSED`).
  - Presentation in PWA: Labelled as `Academic Year: 2023-2024` and `Window: Not published / Closed (CLOSED)`.
- **What Changed vs 2024–25:** Fabricated 2025–26 window removed; recorded honestly as a 2023–24 one-time relief scheme with no confirmed 2025–26 continuation (`window_open_date: None, window_close_date: None, portal_status: CLOSED`).

### 3. SCH-MN-005: Post-Matric Scholarship for ST Students - Manipur
- **Issuing Level:** Centrally Sponsored Scheme (CSS)
- **Governing Ministry:** Ministry of Tribal Affairs (MoTA), Government of India / Department of Tribal Affairs & Hills, Manipur
- **Official Guideline URL:** `https://scholarships.gov.in/public/schemeGuidelines/EDUPostMatricScholarshipPMSforSTstudents.pdf`
- **Content SHA256:** `eb53bc37acc93eccbe811f648e7e741ea05b607db796dc1b759cc8e987256efe`
- **Guideline Document Description:** Centrally Sponsored Scheme of Post-Matric Scholarship for ST Students, Ministry of Tribal Affairs (MoTA), Government of India, 4 pages.
- **Guideline Publication Date:** `2022-04-01` (revised guidelines under 15th Finance Commission Cycle 2021–22 to 2025–26).
- **Key Statutory Eligibility Clauses:**
  - Domicile: Manipur.
  - Social Category: Scheduled Tribe (`ST`).
  - Family Income Ceiling: Maximum ₹2,50,000 per annum.
  - Course Level: Post-Matriculation / Higher Secondary, Undergraduate, Postgraduate, Diploma.
  - Academic Marks Cutoff: None.
- **Academic Year 2025–2026 Window:**
  - Application Window: 2025-06-02 to 2025-10-31
  - Window Status: **CLOSED** (closed on 2025-10-31)
  - Portal Registration: NSP 2.0 (requires Aadhaar OTR Face RD)
  - Official Timeline Source: National Scholarship Portal (`https://scholarships.gov.in`) and Manipur DUHE / College Notice Ref. `HE/NSP/2025-26`.
- **What Changed vs 2024–25:** Application window dates updated from AY 2024–25 to AY 2025–26 (2025-06-02 to 2025-10-31, closed); 4-tier group maintenance allowance rates verified.

### 4. SCH-MN-006: Pre-Matric Scholarship for ST Students (Classes IX & X) - Manipur
- **Issuing Level:** Centrally Sponsored Scheme (CSS)
- **Governing Ministry:** Ministry of Tribal Affairs (MoTA), Government of India
- **Official Guideline URL:** `https://scholarships.gov.in/public/schemeGuidelines/guidelines-Pre-matric-ST.pdf`
- **Content SHA256:** `8e35745e3319bfe532502d9c28e49d6ce704ec1a95a87bd7e983631b1a99474b`
- **Guideline Document Description:** MoTA Revised Scheme Guidelines for Pre-Matric Scholarship for ST Students (Classes IX & X), 12 pages.
- **Guideline Publication Date:** `2022-04-01` (15th Finance Commission Cycle).
- **Key Statutory Eligibility Clauses:**
  - Domicile: Manipur.
  - Social Category: Scheduled Tribe (`ST`).
  - Family Income Ceiling: Maximum ₹2,50,000 per annum.
  - Course Level: Class 9 or Class 10 (`CLASS_9_10`).
- **Academic Year 2025–2026 Window:**
  - Application Window: 2025-06-02 to 2025-10-31
  - Window Status: **CLOSED** (closed on 2025-10-31)
  - Portal Registration: NSP 2.0
  - Official Timeline Source: National Scholarship Portal (`https://scholarships.gov.in`).
- **What Changed vs 2024–25:** Application window dates updated from AY 2024–25 to AY 2025–26 (2025-06-02 to 2025-10-31, closed).

### 5. SCH-MN-007: Post-Matric Scholarship for OBC Students - Manipur
- **Issuing Level:** Centrally Sponsored Scheme (PM-YASASVI)
- **Governing Ministry:** Ministry of Social Justice and Empowerment (MoSJE), Government of India
- **Official Guideline URL:** `https://scholarships.gov.in/public/schemeGuidelines/Centrally%20Sponsored%20Scheme%20of%20Post%20Matric%20Scholarship%20Scheme%20for%20OBC_scheme.pdf`
- **Content SHA256:** `3e7cea65397d06b42644681257beea11193aff243a5aa398818f6f2c2dbfdaf5`
- **Guideline Document Description:** PM Young Achievers Scholarship Award Scheme for Vibrant India (PM-YASASVI) Post-Matric Scholarship for OBC Students, MoSJE, Government of India, 18 pages.
- **Guideline Publication Date:** `2021-04-01` (applicable 2021–22 to 2025–26).
- **Key Statutory Eligibility Clauses:**
  - Domicile: Manipur.
  - Social Category: Other Backward Classes (`OBC`).
  - Family Income Ceiling: Maximum ₹2,50,000 per annum.
  - Course Level: Post-Matriculation, Undergraduate, Postgraduate, Diploma.
- **Academic Year 2025–2026 Window:**
  - Application Window: 2025-06-02 to 2025-10-31
  - Window Status: **CLOSED** (closed on 2025-10-31)
  - Portal Registration: NSP 2.0
  - Official Timeline Source: National Scholarship Portal (`https://scholarships.gov.in`).
- **What Changed vs 2024–25:** Application window dates updated from AY 2024–25 to AY 2025–26 (2025-06-02 to 2025-10-31, closed).

### 6. SCH-MN-009: Post-Matric Scholarship for SC Students - Manipur
- **Issuing Level:** Centrally Sponsored Scheme (CSS)
- **Governing Ministry:** Ministry of Social Justice and Empowerment (MoSJE), Government of India
- **Official Guideline URL:** `https://scholarships.gov.in/public/schemeGuidelines/Postmatric_SC.pdf`
- **Content SHA256:** `cf73697baff4d7ebaf5919363296479b501ea9efc146a27de50623a9472cfa57`
- **Guideline Document Description:** Centrally Sponsored Scheme of Post-Matric Scholarship for SC Students, MoSJE, Government of India, 18 pages.
- **Guideline Publication Date:** `2021-04-01` (applicable 2021–22 to 2025–26).
- **Key Statutory Eligibility Clauses:**
  - Domicile: Manipur.
  - Social Category: Scheduled Caste (`SC`).
  - Family Income Ceiling: Maximum ₹2,50,000 per annum.
  - Course Level: Post-Matriculation, Undergraduate, Postgraduate, Diploma.
- **Academic Year 2025–2026 Window:**
  - Application Window: 2025-06-02 to 2025-10-31
  - Window Status: **CLOSED** (closed on 2025-10-31)
  - Portal Registration: NSP 2.0
  - Official Timeline Source: National Scholarship Portal (`https://scholarships.gov.in`).
- **What Changed vs 2024–25:** Application window dates updated from AY 2024–25 to AY 2025–26 (2025-06-02 to 2025-10-31, closed).

---

## 5. Decoupled Window Status Derivation & API Contracts

### Evaluator Window Derivation Logic
In [`src/modules/eligibility/domain/scheme_evaluator.py`](file:///D:/2026/schemesaathi/src/modules/eligibility/domain/scheme_evaluator.py#L31-L55):
```python
def _derive_window_info(
    window: SchemeApplicationWindow | None,
) -> tuple[str, str | None, str | None, str | None, RuleOutcome, str]:
    today = date.today()
    portal_type_val = window.portal_type.value if window else None
    portal_status_val = window.portal_status.value if window else None
    window_close_val = (
        str(window.window_close_date) if window and window.window_close_date else None
    )

    if window and window.window_open_date is not None and window.window_close_date is not None:
        if window.window_open_date <= today <= window.window_close_date:
            derived_window_status = "OPEN"
            w_diag = f"Application window is OPEN (dates: {window.window_open_date} to {window.window_close_date})."
            w_outcome = RuleOutcome.PASS
        else:
            derived_window_status = "CLOSED"
            w_diag = (
                f"Application window is CLOSED (closed on: {window_close_val or 'Unspecified'})."
            )
            w_outcome = RuleOutcome.FAIL
    else:
        derived_window_status = "CLOSED"
        w_diag = f"Application window is CLOSED (closed on: {window_close_val or 'Unspecified'})."
        w_outcome = RuleOutcome.FAIL

    return (
        derived_window_status,
        portal_type_val,
        portal_status_val,
        window_close_val,
        w_outcome,
        w_diag,
    )
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
      "outcome": "FAIL",
      "explanation_en": "Application window is CLOSED (closed on: 2025-10-31).",
      "missing_fields": []
    }
  ],
  "missing_fields": [],
  "ineligibility_reasons": [],
  "official_source_url": "https://scholarships.gov.in/public/schemeGuidelines/EDUPostMatricScholarshipPMSforSTstudents.pdf",
  "portal_type": "NSP_2_0",
  "portal_status": "CLOSED",
  "window_status": "CLOSED",
  "status_label": "Eligible by rules, window closed",
  "academic_year": "2025-2026",
  "window_close_date": "2025-10-31"
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
      "outcome": "FAIL",
      "explanation_en": "Application window is CLOSED (closed on: 2025-10-31).",
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
  "window_close_date": "2025-10-31"
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
| **Group II** | Other Professional & Technical courses, Post-Graduate degrees, M.Phil, Ph.D. | **₹820** | **₹530** |
| **Group III** | General Graduate degrees (B.A., B.Sc., B.Com.) and equivalent certification courses | **₹570** | **₹300** |
| **Group IV** | Higher Secondary (Class XI & XII), Vocational courses at +2 stage, ITI courses | **₹380** | **₹230** |

---

## 7. Grounded Chat Factual Verifications & Golden Conversations

Executed against [`tests/integration/test_golden_conversations.py`](file:///D:/2026/schemesaathi/tests/integration/test_golden_conversations.py):
- **GC1 (Eligibility Synchronization):** Assistant evaluates ST Manipur student, producing structured eligibility items with `status: "ELIGIBLE"`, `window_status: "CLOSED"`, `status_label: "Eligible by rules, window closed"`.
- **GC2 (Factual Allowance Query):** Group I Post-Matric ST inquiry correctly produces ₹550/month day scholar allowance with inline citation `[^1]`.
- **GC3 (Out-of-Corpus Query):** Unsupported scholarship inquiry triggers `STANDARD_REFUSAL_MESSAGE` (0 ungrounded claims).
- **GC4 (Application Window Query):** Application timeline query produces factual closing date `2025-10-31` with `[^1]` citation.
- **GC5 (State Synchronization):** Mid-conversation profile updates update eligibility dynamically without desynchronization.
- **GC6 (Multilingual Meiteilon / Meetei Mayek):** Romanized and script queries maintain grounded citations and statutory values.
- **GC7 (Document Readiness Auditor):** Produces statutory document checklist with mandatory NPCI APB warning.
- **GC8 (Prompt Injection Probe):** Refuses adversarial jailbreaks attempting to bypass AST logic or drop citations.
- **GC9 (Pan-India Guardrail):** Queries from non-Manipur domiciles are handled strictly with statutory notifications.

---

## 8. Test Suite Execution & CI Pipeline Verification

### Test Summary
```text
============================= test session starts =============================
platform win32 -- Python 3.12.14, pytest-9.2.0, pluggy-1.7.0 -- D:\2026\schemesaathi\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\2026\schemesaathi
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.16.0, asyncio-1.4.1.post1, cov-7.1.0
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=function, asyncio_default_test_loop_scope=function
collecting ... collected 204 items

[... 204 items executed across unit and integration suites ...]

=========================== short test summary info ===========================
SKIPPED [1] tests\integration\test_postgres_pgvector_integration.py:89: PostgreSQL 16 + pgvector instance is not reachable (local non-CI run)
SKIPPED [1] tests\integration\test_postgres_pgvector_integration.py:192: PostgreSQL 16 + pgvector instance is not reachable (local non-CI run)
SKIPPED [1] tests\integration\test_postgres_pgvector_integration.py:261: PostgreSQL 16 + pgvector instance is not reachable (local non-CI run)
SKIPPED [1] tests\integration\test_postgres_retrieval_integration.py:100: PostgreSQL 16 + pgvector instance is not reachable (local non-CI run)
SKIPPED [1] tests\integration\test_postgres_retrieval_integration.py:114: PostgreSQL 16 + pgvector instance is not reachable (local non-CI run)
SKIPPED [1] tests\integration\test_postgres_retrieval_integration.py:130: PostgreSQL 16 + pgvector instance is not reachable (local non-CI run)
SKIPPED [1] tests\integration\test_postgres_retrieval_integration.py:158: PostgreSQL 16 + pgvector instance is not reachable (local non-CI run)
SKIPPED [1] tests\integration\test_postgres_retrieval_integration.py:177: PostgreSQL 16 + pgvector instance is not reachable (local non-CI run)
============ 196 passed, 8 skipped, 1 warning in 184.44s (0:03:04) ============
```

### Static Analysis & CI Pipeline Verification
- **GitHub Actions Run ID:** [42743168818](https://github.com/mithilesh1627/schemesaathi/actions/runs/42743168818)
- **Commit:** `1a4357c` (`docs(phase-a): record verified green CI run in Phase A report`)
- **Job 1 (Code Quality):** `completed / success` (Ruff lint, Ruff format check, Mypy strict typing across 91 source files).
- **Job 2 (Automated Unit & Integration Tests):** `completed / success` (All 204 items passed against live PostgreSQL 16 + pgvector container and Redis cluster; 90% code coverage).
- **Local Checks:**
  - `ruff check .` -> `All checks passed!`
  - `ruff format --check .` -> `120 files already formatted`
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
   *(Expected: 196 passed, 8 skipped (database integration tests requiring live PostgreSQL/pgvector), 0 failed).*

4. **Verify Payload Budget Measurement:**
   ```powershell
   python -c "
   import asyncio
   from httpx import AsyncClient, ASGITransport
   from src.main import app

   async def check():
       routes = ['/', '/manifest.json', '/sw.js', '/static/app.css', '/static/app.js',
                 '/static/icons/icon-192.svg', '/static/icons/icon-192.png',
                 '/static/icons/icon-512.png']
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

## 10. Known Limitations & Scope Boundaries

1. **Phase A Scope Boundary:** Phase A strictly encompasses statutory dataset refresh, window status decoupling, and contract alignment. It does **not** constitute a public launch or full production sign-off.
2. **Carried-Over Known Limitations Left Intact:**
   - Source registry list is hard-coded in `source_registry_service.py`.
   - Chunked-transfer requests bypass the request-size middleware.
   - Docker healthcheck verifies process liveness only.
   - UNKNOWN outcomes are stored in the audit DB as `CONDITIONALLY_ELIGIBLE`.
   - CI live-OCR covers only page 1 of the 18-page SC guideline (full coverage depends on the committed OCR cache).
   - CMCSRS provenance URL is an official department notification page rather than the guideline PDF itself.
   - Chat sessions are stored in-memory only.
   - SSE streaming tokens are simulated.
   - Student profile `is_displaced` defaults to `False` when unknown.
   - Multi-group numeric grounding checker rule triggers only on allowance/day-scholar/hosteller/stipend terms.
3. **PostgreSQL 16 + pgvector Integration Tests:** The 8 integration tests requiring an active live PostgreSQL instance and Redis cluster are cleanly skipped in local environments without Docker services running, and pass in full CI runner environments with services configured.
4. **Field Pilot Protocol:** The field pilot protocol prepared in `docs/pilot/field_pilot_protocol.md` remains documented and ready for execution, but has **not** been run (in line with reviewer guidance).
5. **Subsequent Hardening (Production Phase B & C):**
   - Phase B: Production deployment configuration, security headers (CSP, HSTS, X-Content-Type-Options), rate-limiting persistence in Redis, and structured error alerting.
   - Phase C: Load testing on high-concurrency synthetic profiles and automated daily portal window scraping probes.

---

### Final Recommendation
**Ready for reviewer check as a Phase A data refresh**  
*(This phase refreshes the data only — it is not a production launch.)*
