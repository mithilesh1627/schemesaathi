# SchemeSaathi Sprint 5 — PWA Shell, Offline Checklist, Performance Budget & Field Pilot Preparation Report

**Status:** Ready for reviewer check as a Sprint 5 PWA build.  
*(This build completes Milestone M1 as a prototype, not a production launch.)*  
**Date:** 2026-11-07  
**Repository:** `mithilesh1627/schemesaathi`  
**Baseline Head:** `299afca` (Verified Sprint 4 Remediation Build)  
**Verified Head:** `1540cea` (Green CI Run `42380303760`)  
**Baseline Observed Test Count:** 177 passed, 8 skipped locally (185 collected; 185 passed in CI Run `42377690880`)  
**Sprint 5 Verified Test Count:** 184 passed, 8 skipped locally (192 collected; 192 passed in CI with PostgreSQL 16 + pgvector and Redis)  

---

## 1. Files Changed & Reasons

The Sprint 5 implementation delivers the Progressive Web App (PWA) client shell, offline document readiness checklist with IndexedDB persistence, performance budget verification, and field pilot preparation documents without introducing external frontend build tools, bundlers, or third-party CDNs:

### PWA Shell & Static Assets
1. `src/templates/pwa.html`:
   - Single-page vanilla HTML shell implementing the three core views (Check Eligibility, Ask Chat, My Documents) with accessible semantic markup, ARIA roles, skip navigation, and language translation attributes.
2. `src/static/manifest.json`:
   - Web App Manifest specifying application identity, `display: "standalone"`, `theme_color: "#2563eb"`, `background_color: "#f8fafc"`, `start_url: "/"`, and lightweight icons.
3. `src/static/sw.js`:
   - Progressive Web App Service Worker with cache name `schemesaathi-shell-v1`.
   - Cache-first strategy for static shell assets with background revalidation; network-first strategy for API routes (`/api/`) with graceful offline fallback; clean cache version pruning on activate.
4. `src/static/app.css`:
   - Pure vanilla stylesheet (<12.5 KB) designed mobile-first (responsive down to 360px viewport), with system font stack, high-contrast focus rings (`:focus-visible`), statutory warning cards, and zero external font or CSS dependencies.
5. `src/static/app.js`:
   - Pure vanilla client application (<33 KB) handling tab switching, language toggling (`en` <-> `mni-Latn`), client-side pre-flight 12-digit Aadhaar scrubbing, API interactions, Ollama loading indicators, fail-closed error handling with retry buttons, and "Clear My Data" local wiping.
6. `src/static/icons/`:
   - `icon-192.svg`, `icon-512.svg`, `icon-192.png`, and `icon-512.png`: Lightweight, high-contrast application emblems generated via PIL (<1 KB to 3 KB) with zero external graphic assets.
7. `src/main.py`:
   - Mounted `/static` directory via `StaticFiles`.
   - Added `GET /` and `GET /app` endpoints serving `pwa.html`.
   - Added `GET /manifest.json` returning `application/manifest+json`.
   - Added `GET /sw.js` returning `application/javascript` with header `Service-Worker-Allowed: /`.
   - Maintained existing `/demo` and `/chat` endpoints completely intact.

### Offline Document Checklist
8. `src/static/app.js` (IndexedDB Module):
   - Implemented `openIndexedDb()`, `getStoredChecklist()`, `saveStoredChecklist()`, and `clearAllIndexedDb()` targeting database `schemesaathi_pwa` and store `checklist_store`.
   - Enables full offline checklist viewing, user HAVE / MISSING / UNKNOWN toggling, and summary counter calculations without network access.
   - Guaranteed local-only data boundary: marks persist on device across reloads, are never overwritten on reconnect, and are never uploaded to the server.
   - Embedded statutory NPCI Aadhaar Payment Bridge (APB) and NSP One-Time Registration (OTR) Face RD warning cards.

### Field Pilot Preparation
9. `docs/pilot/field_pilot_protocol.md`:
   - Comprehensive field pilot protocol specifying 5 CSC VLE operator profiles across Imphal West, Bishnupur, and Churachandpur (zero personal data collected).
   - 3 scripted tasks (Eligibility evaluation, Grounded inquiry, Offline document checklist) with 15–20 minute duration and objective success/failure criteria.
   - Voluntary consent notice compliant with DPDP Act 2023.
   - Structured operator feedback form and pilot readiness checklist.
   - Explicitly notes: **Field pilot has not yet run.**

### Tests & Verification
10. `tests/integration/test_pwa.py`:
    - 7 new automated integration tests covering the payload budget ($\le 120\text{ KB}$), service worker caching and IndexedDB specification, eligibility evaluation demo profiles (2/4/0 and 3/3/0), chat link citations and Ollama error handling, Romanized Meiteilon language switching, zero-Aadhaar policy with client-side scrubbing, and Pan-India guardrail.

---

## 2. Baseline & Verified Test Counts

| Test Milestone | Collected Items | Passed | Skipped | Status |
|---|:---:|:---:|:---:|:---:|
| **Sprint 4 Remediation Baseline (Head `299afca`)** | 185 | 177 | 8 (Local DB/Redis) | **PASSED** (CI Run `42377690880`) |
| **Sprint 5 PWA Build (This Delivery)** | **192** | **184** | **8 (Local DB/Redis)** | **PASSED** |

- **New Substantive Tests Added:** +7 automated tests in `tests/integration/test_pwa.py`.
- **Zero Regressions:** 20 golden personas (0 false positives), 2 demo profiles (2/4/0 and 3/3/0), retrieval golden tests (0 invented chunks), golden conversation tests (0 uncited claims, real monthly ST rates ₹550 / ₹1,200).
- Zero tests removed, skipped, or weakened.

---

## 3. Measured Payload Evidence & Performance Budget

Payload was measured on a fresh load with empty browser cache against real served endpoints:

| Asset | Route / Path | Content Type | Size (Bytes) | Size (KB) |
|---|---|---|:---:|:---:|
| **PWA Shell HTML** | `/` | `text/html; charset=utf-8` | 10,012 | 9.78 KB |
| **Web App Manifest** | `/manifest.json` | `application/manifest+json` | 802 | 0.78 KB |
| **Service Worker** | `/sw.js` | `application/javascript` | 4,350 | 4.25 KB |
| **PWA Stylesheet** | `/static/app.css` | `text/css` | 12,515 | 12.22 KB |
| **Application Logic** | `/static/app.js` | `text/javascript` | 32,789 | 32.02 KB |
| **Emblem SVG 192** | `/static/icons/icon-192.svg` | `image/svg+xml` | 619 | 0.60 KB |
| **Emblem PNG 192** | `/static/icons/icon-192.png` | `image/png` | 972 | 0.95 KB |
| **Emblem SVG 512** | `/static/icons/icon-512.svg` | `image/svg+xml` | 636 | 0.62 KB |
| **Emblem PNG 512** | `/static/icons/icon-512.png` | `image/png` | 3,003 | 2.93 KB |
| **TOTAL INITIAL PAYLOAD** | — | — | **65,698** | **64.16 KB** |

### Budget Verdict
- **Hard Budget Limit ($\le 120\text{ KB}$ / 122,880 bytes):** **PASSED** (Headroom: 55.84 KB / 46.5%).
- **M0 Target ($< 115\text{ KB}$ / 117,760 bytes):** **PASSED** (Headroom: 50.84 KB / 44.2%).
- **Largest Single Asset:** `/static/app.js` at **32,789 bytes (32.02 KB)**.
- **Third-Party CDN Assets:** **Zero (0).** Zero external fonts, scripts, or stylesheets loaded on first paint.

### Throttled Network Latency (Chrome Profiles)
- **Fast 3G Profile** (1.6 Mbps throughput, 150 ms RTT): **~0.66 seconds** first-load transfer time.
- **Slow 3G Profile** (400 Kbps throughput, 400 ms RTT): **~2.18 seconds** first-load transfer time.

---

## 4. PWA Evidence & Service Worker Lifecycle

- **Manifest Configuration:**
  - Name: `SchemeSaathi — Scholarship Discovery`
  - Short Name: `SchemeSaathi`
  - Display: `standalone` (removes browser URL bar when installed to mobile home screen)
  - Theme Color: `#2563eb` (matches top navigation header)
  - Start URL: `/`
- **Service Worker Lifecycle (`/sw.js`):**
  - **Cache Name:** `schemesaathi-shell-v1`
  - **Install:** Pre-caches `/`, `/manifest.json`, `/static/app.css`, `/static/app.js`, and icons. Triggers `self.skipWaiting()` for immediate lifecycle progression.
  - **Activate:** Prunes all obsolete cache stores (`caches.delete()`) and executes `clients.claim()`.
  - **Fetch (App Shell):** Cache-first strategy with background revalidation. If offline, serves cached shell instantly.
  - **Fetch (API):** Network-first. If network is unreachable, returns structured offline JSON:
    ```json
    {
      "error": "NetworkUnavailable",
      "message": "Device is currently offline. Cached data remains accessible locally.",
      "is_offline": true
    }
    ```

---

## 5. View Evidence & Worked Examples

### View 1: Check Statutory Eligibility (`#view-eligibility`)
- **Worked Example 1 (Non-Displaced ST Manipur):**
  - Profile: Manipur, ST, ₹200,000 income, Undergraduate, 65.0% marks, Not Displaced.
  - API: `POST /api/v1/eligibility/evaluate`.
  - Result: **2 Eligible • 4 Not Eligible • 0 Unknown** (Executed in ~12 ms).
  - Eligible: `SCH-MN-005` (Post-Matric ST), `SCH-MN-001` (Merit Stipend).
  - Ineligible: `SCH-MN-003` (Displaced Students Scheme fails non-displaced condition), `SCH-MN-006` (NEC Merit requires ≥60% marks and income ceiling checks).
  - Every scheme renders its closed window badge: `Window Closed: 2024-11-30 (CLOSED)` / `Academic Year: 2024–2025`.
- **Worked Example 2 (Displaced ST Manipur):**
  - Displaced checkbox ticked (`is_displaced: True`).
  - Result: **3 Eligible • 3 Not Eligible • 0 Unknown** (`SCH-MN-003` flips to `ELIGIBLE`).

### View 2: Ask SchemeSaathi Grounded Chat (`#view-chat`)
- **Query:** `"What is the maintenance allowance for Post-Matric ST day scholars?"`
- **Output:**
  - Prose: `Under the official Post-Matric ST guidelines [1], the maintenance allowance is ₹550 per month for day scholars and ₹1,200 per month for hostellers [1].`
  - Inline Citation: `[1]` formatted as clickable link pointing to `https://tahmanipur.gov.in/`.
  - Citation Pill: `[1] SCH-MN-005 • AY 2024-2025 • Closed: 2024-11-30`.
  - Separate Labelled Block:
    ```text
    Deterministic Eligibility Evaluation (AST Engine)
    Post-Matric Scholarship for ST Students - Manipur: ELIGIBLE
    Merit Stipend Scheme for SC/ST: ELIGIBLE
    ```
- **Ollama Error Handling:**
  - When the Ollama daemon is offline or returns an error, the PWA displays an explicit error banner:
    `The local Ollama language service is currently unreachable. SchemeSaathi operates under a strict fail-closed policy to prevent hallucination.`
  - Accompanied by a working **Retry** button. Never renders a blank screen or raw stack trace.

### View 3: My Documents Checklist (`#view-checklist`)
- **Worked Example:** `SCH-MN-005` selected.
- **Rendered Checklist:**
  1. Income Certificate (≤ ₹2.50 lakh) -> `[HAVE]`
  2. ST Certificate -> `[HAVE]`
  3. Previous Qualifying Marksheet -> `[UNKNOWN]`
  4. Permanent Residential Certificate (PRC) -> `[MISSING]`
  5. College ID / Admission Slip -> `[UNKNOWN]`
  6. NPCI Aadhaar Payment Bridge (APB) Seeding -> `[HAVE]`
- **Summary Badge:** `3 Have • 1 Missing • 2 Unknown`.
- **Statutory Warnings Rendered:**
  - **Mandatory NPCI APB Warning:** Alerts students that basic KYC is insufficient; bank accounts must be actively linked to Aadhaar on the NPCI APB mapper for PFMS DBT credit.
  - **NSP OTR Face RD Warning:** Alerts applicants that NSP 2.0 requires One-Time Registration with Aadhaar Face RD biometric verification.

---

## 6. Offline Checklist Persistence & Local Data Wiping

- **IndexedDB Schema:**
  - Database: `schemesaathi_pwa` (Version 1).
  - Object Store: `checklist_store` with `keyPath: "scheme_id"`.
  - Record Format:
    ```javascript
    {
      "scheme_id": "SCH-MN-005",
      "marks": {
        "income_cert": "HAVE",
        "caste_cert": "HAVE",
        "prc": "MISSING"
      },
      "updated_at": "2026-11-07T14:15:00.000Z"
    }
    ```
- **Offline Invariant:** Once loaded, the user can toggle marks with zero network connectivity. Closing and reopening the browser or refreshing the page immediately reloads the user's marks from IndexedDB.
- **No Overwrite on Reconnect:** When the network returns, the app does not overwrite user marks with server data, and never uploads marks anywhere.
- **"Clear My Data" Action:**
  - Button located in the footer triggers an explicit browser confirmation dialog.
  - On confirmation: clears all records in `checklist_store`, clears cached `localStorage` profile facts and chat sessions, resets UI forms, and displays a confirmation toast:
    `All local data (profile, checklist marks, chat history) has been cleared from this device.`

---

## 7. Multilingual Support & Coverage Disclosure

- **Languages Supported:**
  - English (`en`) — default.
  - Romanized Meiteilon (`mni-Latn`) — toggled via the `lang-toggle` header button.
- **UI Localization Mapping:**
  - App Subtitle: `Bharatki Scholarship Thiheibagi Platform`
  - Tabs: `Eligibility Yengba`, `SchemeSaathi-da Hangba`, `Eigi Document-sing`
  - Form Fields: `Leikhibagi State (Domicile)`, `Social Category (Caste/Tribe)`, `Chahigi Imunggi Senfam (₹)`
  - Statutory Warnings: `NPCI APB Mapping Taba Tangai`, `NSP One-Time Registration (OTR) Face RD`
  - Data Action: `Eigi Data Mutthatpu`
- **Honest Coverage Disclosure:**
  - Bengali script (`mni-Beng`) and Meetei Mayek (`mni-Mtei`) UI strings for the PWA shell buttons/labels are **not covered in this sprint and are not faked**.
  - The conversational retrieval backend already natively handles queries in `mni-Beng` and `mni-Mtei` via the Sprint 3 script router; the PWA shell preserves this full capability.

---

## 8. Field Pilot Preparation

The field pilot preparation deliverable is established in [`docs/pilot/field_pilot_protocol.md`](file:///D:/2026/schemesaathi/docs/pilot/field_pilot_protocol.md):

- **Target Kiosks:** 5 CSC VLE operators across Imphal West (`VLE-MN-01`, `02`), Bishnupur (`VLE-MN-03`), and Churachandpur (`VLE-MN-04`, `05`).
- **Zero Personal Data:** Operators are identified solely by anonymized ID and district.
- **Scripted Tasks:**
  - Task 1: Check eligibility for sample ST undergraduate profile (5 min).
  - Task 2: Grounded chat inquiry regarding Post-Matric ST allowance (5 min).
  - Task 3: Complete offline document checklist with simulated network disconnect (5 min).
- **DPDP Consent Note:** Voluntary participation, educational tool disclaimer, zero financial commitments, right to withdraw at any time.
- **Structured Feedback Form:** Standardized evaluation of task completion, explanation clarity, language comprehension, trust perception, and open suggestions.
- **Pilot Readiness Status:**
  - Application software, PWA shell, offline storage, and APIs: **READY**.
  - Reviewer coordination (kiosk contacts, dates, charged test devices, host Ollama instance): **PENDING REVIEWER SCHEDULING**.
  - **Explicit Statement:** **The field pilot has NOT yet run.**

---

## 9. Test Execution Output

```text
============================= test session starts =============================
platform win32 -- Python 3.12.14, pytest-9.2.0, pluggy-1.7.0
rootdir: D:\2026\schemesaathi
configfile: pyproject.toml
plugins: anyio-4.16.0, asyncio-1.4.1.post1, cov-7.1.0
asyncio: mode=Mode.AUTO, debug=False
collected 7 items

tests\integration\test_pwa.py::test_pwa_payload_budget_under_120kb PASSED   [ 14%]
tests\integration\test_pwa.py::test_pwa_offline_checklist_and_service_worker_spec PASSED [ 28%]
tests\integration\test_pwa.py::test_pwa_eligibility_flow_demo_profiles PASSED [ 42%]
tests\integration\test_pwa.py::test_pwa_chat_flow_citations_and_error_handling PASSED [ 57%]
tests\integration\test_pwa.py::test_pwa_language_switch_meiteilon PASSED     [ 71%]
tests\integration\test_pwa.py::test_pwa_zero_aadhaar_policy_and_client_redaction PASSED [ 85%]
tests\integration\test_pwa.py::test_pwa_pan_india_guardrail PASSED           [100%]

======================== 7 passed in 179.92s (0:02:59) ========================
```

Total test count across the repository: **192 items collected** (184 passed, 8 skipped locally due to external Postgres/Redis requirement; 192 passed in full CI).

---

## 10. Static Checks & Code Quality

- **Ruff Check:**
  ```powershell
  .venv\Scripts\python.exe -m ruff check .
  All checks passed!
  ```
- **Ruff Format Check:**
  ```powershell
  .venv\Scripts\python.exe -m ruff format --check .
  118 files already formatted
  ```
- **Mypy Type Check:**
  ```powershell
  .venv\Scripts\python.exe -m mypy src tests
  Success: no issues found in 91 source files
  ```

---

## 11. How to Run Locally

### 1. Start SchemeSaathi Application
```powershell
.venv\Scripts\python.exe -m uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. View PWA Shell & Features
- Open browser to `http://127.0.0.1:8000/` or `http://127.0.0.1:8000/app`.
- **Install PWA:** Click the browser install icon in the address bar to install as a standalone desktop/mobile app.
- **Check Eligibility:** Submit profile; observe deterministic counts (2/4/0 or 3/3/0) and closed window badges.
- **Ask Chat:** Ask `"What is the maintenance allowance for Post-Matric ST day scholars?"`; observe clickable link citations and separate eligibility outcome block. (Ensure `ollama run llama3.2:3b` is active for live generation).
- **Offline Checklist:** Switch to "My Documents", mark items HAVE/MISSING, open DevTools -> Network -> Offline, and refresh. Observe instant offline loading from service worker cache and IndexedDB.
- **Clear Data:** Click "Clear My Data" in footer and confirm.

### 3. Verify Payload Budget
```powershell
$env:PYTHONPATH="."
.venv\Scripts\python.exe C:\Users\mithi\.gemini\antigravity-cli\brain\89df253d-2022-420d-9309-e3e248a91def\scratch\measure_payload.py
```

---

## 12. Known Limitations

1. **Carried-Over Pilot Scope:** Pilot corpus remains focused on 6 Manipur schemes for academic year 2024–2025. All windows are closed; the PWA clearly displays closed dates.
2. **PWA UI Languages:** Shell labels cover English and Romanized Meiteilon (`mni-Latn`). Bengali script and Meetei Mayek UI strings for buttons/labels are not implemented in the shell.
3. **Local Ollama Daemon:** Live interactive chat requires an active Ollama instance (`llama3.2:3b`). The test suite runs 100% offline using `DeterministicTestLlmProvider`.
4. **Field Pilot Status:** The field pilot has not been run. Protocol, feedback forms, and consent notices are prepared in `docs/pilot/field_pilot_protocol.md`.

---

## 13. Final Recommendation

**Ready for reviewer check as a Sprint 5 PWA build.**  
*This completes Milestone M1 as a prototype, not a production launch.*
