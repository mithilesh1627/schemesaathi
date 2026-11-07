# SchemeSaathi Milestone M1 — Field Pilot Protocol

**Document Version:** 1.0  
**Date:** 2026-11-07  
**Scope:** Closed Field Pilot Preparation with 5 CSC Village Level Entrepreneurs (VLEs) across 3 Districts in Manipur.  
**Pilot Status:** **PREPARATION ONLY — NOT EXECUTED.**  
*(This protocol specifies the preparation deliverables. No field testing has yet been conducted, and no pilot feedback or results are claimed. Execution will be scheduled by the reviewer.)*

---

## 1. Pilot Purpose & Scope

The SchemeSaathi Field Pilot is an operational test designed to evaluate the usability, language clarity, and offline reliability of the SchemeSaathi Progressive Web App (PWA) in real-world CSC kiosk environments across Manipur.

### Target Objectives:
1. Verify whether CSC VLE operators can evaluate student eligibility without technical assistance.
2. Verify operator comprehension of deterministic reasoning and closed statutory application windows.
3. Assess the usability of the offline document readiness checklist on low-end mobile devices and kiosk browsers.
4. Gather structured feedback on language clarity (English and Romanized Meiteilon) and UI responsiveness.

---

## 2. Operator Profiles (Non-Personal Data)

To protect operator privacy compliant with the Digital Personal Data Protection (DPDP) Act 2023, zero personal data (no names, phone numbers, Aadhaar numbers, or email addresses) is recorded. Operators are identified solely by role and district:

| Operator ID | Kiosk Role | District | Typical Citizen Demographics | Device / Environment |
|---|---|---|---|---|
| **VLE-MN-01** | CSC Village Level Entrepreneur | Imphal West | Urban & Peri-Urban Meitei / General students | Desktop Browser / Android Phone |
| **VLE-MN-02** | CSC Village Level Entrepreneur | Imphal West | Urban college students & displaced applicants | Android Phone (Chrome) |
| **VLE-MN-03** | CSC Village Level Entrepreneur | Bishnupur | Rural agricultural families / OBC students | Low-end Mobile Device (3G/4G) |
| **VLE-MN-04** | CSC Village Level Entrepreneur | Churachandpur | Hill district tribal students (ST) | Android Tablet / Kiosk PC |
| **VLE-MN-05** | CSC Village Level Entrepreneur | Churachandpur | Conflict-displaced tribal students | Mobile Device (Offline environment) |

---

## 3. Scripted Evaluation Tasks

The pilot consists of three discrete, timed tasks taking approximately **15 to 20 minutes** total per operator:

### Task 1: Check Statutory Eligibility (Duration: 5 minutes)
- **Scripted Scenario:** A student visits the kiosk asking for college scholarship options. The student is a permanent resident of Manipur, belongs to the Scheduled Tribe (ST) category, has an annual family income of ₹2,00,000, is studying undergraduate degree with 65% marks, and is not displaced.
- **Operator Action:**
  1. Open SchemeSaathi PWA (`/` or `/app`).
  2. Select "Check Eligibility" view.
  3. Enter the profile parameters: `Manipur`, `ST`, `₹200,000`, `Undergraduate`, `65.0%`, Non-displaced.
  4. Click "Evaluate Statutory Eligibility".
- **Success Criteria:**
  - Operator views the result summary: **2 Eligible, 4 Not Eligible, 0 Unknown**.
  - Operator observes that Post-Matric ST (`SCH-MN-005`) and Merit Stipend (`SCH-MN-001`) are marked `ELIGIBLE`.
  - Operator notes the closed window banner: Academic Year 2024–2025 (Window Closed: `2024-11-30`).
- **Failure Criteria:**
  - Operator is unable to find or submit the form.
  - Operator mistakes a closed scheme for an actively open application.

### Task 2: Grounded Inquiry / Chat (Duration: 5 minutes)
- **Scripted Scenario:** The student asks how much monthly maintenance allowance they will receive as a day scholar under the Post-Matric ST scholarship.
- **Operator Action:**
  1. Switch to "Ask SchemeSaathi" view.
  2. Enter query: `"What is the maintenance allowance for Post-Matric ST day scholars?"`.
  3. Review the returned answer, citation pills, and separate eligibility box.
- **Success Criteria:**
  - Response clearly states **₹550 per month** for day scholars (and/or ₹1,200/month for hostellers), cited with `[^1]`.
  - Clicking the citation link opens the official guideline portal source URL.
  - The deterministic eligibility engine results are rendered in a distinct, separate labelled box.
  - If the Ollama service is unavailable, a plain-language error banner is shown with a retry button (no blank screens or raw stack traces).
- **Failure Criteria:**
  - Uncited parametric knowledge is displayed, or wrong figures (e.g. ₹7,000 / ₹13,500) appear.
  - A blank screen or uncaught exception occurs.

### Task 3: Offline Document Readiness Checklist (Duration: 5 minutes)
- **Scripted Scenario:** The student wants to know what documents they need to prepare before the next portal cycle. The operator disconnects network / turns on Airplane Mode to test kiosk resilience.
- **Operator Action:**
  1. Switch to "My Documents" view.
  2. Select `SCH-MN-005` (Post-Matric ST).
  3. Mark Income Certificate and ST Certificate as `HAVE`, and PRC as `MISSING`.
  4. Reload the browser page while offline.
  5. Check whether marks persisted and observe the statutory NPCI APB and NSP OTR warnings.
  6. Click "Clear My Data" and verify confirmation toast.
- **Success Criteria:**
  - Document checklist displays immediately from local cache / IndexedDB while offline.
  - Selected marks persist accurately across page reloads.
  - The mandatory NPCI APB warning and NSP OTR Face RD warnings are read and acknowledged.
  - "Clear My Data" successfully clears all local marks with user confirmation.
- **Failure Criteria:**
  - Checklist fails to open offline.
  - Stored marks are lost on reload.
  - The app attempts to upload marks or requests an Aadhaar number.

---

## 4. Informed Consent Note

Every operator must be briefed with the following consent note prior to participating:

> **Volunteer Consent & DPDP Notice:**  
> Participation in this pilot is entirely voluntary. The SchemeSaathi prototype is an educational and statutory discovery tool, not an official application portal.  
> - **Zero Personal Data Collection:** No personal details, applicant names, telephone numbers, bank credentials, or Aadhaar numbers will ever be requested, stored, or processed.  
> - **Operator Anonymity:** Feedback will be recorded strictly under an anonymized operator identifier (`VLE-MN-01` through `05`) and used solely to refine UI usability, language translations, and offline caching.  
> - **No Financial or Application Commitment:** Evaluated schemes are for closed Academic Year 2024–2025 cycles. No real scholarship applications are submitted through this software.  
> - **Right to Withdraw:** Operators may pause or withdraw from the session at any moment without justification.

---

## 5. Structured Operator Feedback Form

*(To be administered after completion of the 3 scripted tasks. No personal data collected.)*

**Operator District:** `[ ] Imphal West   [ ] Bishnupur   [ ] Churachandpur`  
**Operator ID:** `VLE-MN-____`  
**Device Used:** `[ ] Android Phone   [ ] Desktop/Kiosk PC   [ ] Tablet`  

### Usability Evaluation:
1. **Task Completion:**
   - Task 1 (Eligibility Form): `[ ] Completed easily   [ ] Completed with difficulty   [ ] Failed`
   - Task 2 (Ask Chat): `[ ] Completed easily   [ ] Completed with difficulty   [ ] Failed`
   - Task 3 (Offline Checklist): `[ ] Completed easily   [ ] Completed with difficulty   [ ] Failed`

2. **Clarity & Understanding:**
   - Did you understand why certain schemes were marked Eligible vs Not Eligible? `[ ] Yes   [ ] Somewhat   [ ] No`
   - Was the distinction between closed past schemes (AY 2024–2025) and open applications clear? `[ ] Yes   [ ] No`
   - Were the official citation links helpful to verify authority? `[ ] Yes   [ ] Not needed   [ ] Confusing`

3. **Language & Phrasing:**
   - Did you switch to Romanized Meiteilon (`mni-Latn`)? `[ ] Yes   [ ] Kept English`
   - If switched, were the Meiteilon labels natural and easy to understand? `[ ] Very clear   [ ] Understandable   [ ] Unclear / unnatural`
   - Were any specific words or instructions confusing? *(Open text)*: ___________________________

4. **Trust & Safety:**
   - Did anything in the app feel untrustworthy, suspicious, or confusing? `[ ] No   [ ] Yes`
   - Did the app ask for any Aadhaar number or sensitive document upload? `[ ] No (Correct)   [ ] Yes (Report Defect)`
   - Was the NPCI APB warning understandable for explaining DBT account seeding to students? `[ ] Yes   [ ] No`

5. **Overall Feedback / Suggestions:**  
   __________________________________________________________________________

---

## 6. Pilot Readiness Checklist

The following items summarize what is built and ready in SchemeSaathi, and what remains for the reviewer to coordinate:

| Component | Status | Responsible Party | Notes |
|---|:---:|---|---|
| PWA Application Shell (`/`) | **READY** | Repository Build | Served via FastAPI with service worker and manifest |
| Deterministic Eligibility Engine | **READY** | Repository Build | Verified 2/4/0 and 3/3/0 outcomes |
| Grounded Chat & Citations | **READY** | Repository Build | Links to official portals with closed window tags |
| Offline Document Checklist | **READY** | Repository Build | IndexedDB persistence, NPCI/OTR warnings, Clear Data |
| Zero-Aadhaar Client Redaction | **READY** | Repository Build | Redacts 12-digit numbers before network dispatch |
| Kiosk / VLE Operator Recruitment | **PENDING** | Reviewer Coordination | Reviewer to establish contact with 5 CSC VLEs |
| Pilot Date & Location Logistics | **PENDING** | Reviewer Coordination | Schedule 20-minute sessions across Imphal West, Bishnupur, Churachandpur |
| Device Provisioning | **PENDING** | Reviewer Coordination | Ensure 1 charged mobile device / kiosk PC with Chrome/Firefox per operator |
| Local Ollama Daemon Setup | **PENDING** | Reviewer Coordination | Run `ollama run llama3.2:3b` on evaluation host if testing live chat |
