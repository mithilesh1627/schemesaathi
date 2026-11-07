/**
 * SchemeSaathi PWA Client Application
 * Vanilla JavaScript - Zero bundler, zero third-party CDN, <25 KB.
 * Features:
 *  - Service Worker registration & PWA installability
 *  - IndexedDB offline document checklist persistence
 *  - Multilingual UI (English & Romanized Meiteilon 'mni-Latn')
 *  - Client-side pre-flight Aadhaar redaction
 *  - Deterministic statutory eligibility evaluation
 *  - Grounded conversational chat with link citations & separate eligibility block
 *  - Data clearing action with user confirmation
 */

(function () {
  "use strict";

  // --- 1. Multilingual UI Dictionary ---
  const I18N = {
    en: {
      appName: "SchemeSaathi",
      appSubtitle: "Indian Scholarship Discovery",
      pilotBanner: "Demo — Manipur Pilot. Prototype build, not a public launch.",
      tabEligibility: "Check Eligibility",
      tabChat: "Ask SchemeSaathi",
      tabChecklist: "My Documents",
      eligibilityTitle: "Check Statutory Eligibility",
      eligibilityDesc: "Deterministic evaluation against official government guidelines. All 6 pilot schemes are AY 2024–2025 with closed windows.",
      lblDomicile: "Domicile State",
      lblCategory: "Social Category",
      lblIncome: "Annual Family Income (₹)",
      lblCourse: "Course Level",
      lblMarks: "Qualifying Marks (%)",
      lblGender: "Gender",
      lblDisplaced: "Displaced / Conflict-Affected Student (Manipur)",
      btnEvaluate: "Evaluate Statutory Eligibility",
      evaluating: "Evaluating Deterministic Rules...",
      chatTitle: "Grounded Conversational Assistant",
      chatDesc: "Answers grounded strictly in official guideline chunks. Eligibility evaluated only by the deterministic engine.",
      chatPlaceholder: "Ask about scholarship rules, benefits, deadlines...",
      btnSend: "Send",
      loadingOllama: "Checking official guidelines via Ollama (llama3.2:3b)...",
      chatWelcome: "Hello! I am SchemeSaathi. Ask me about scholarship eligibility rules, benefits, or document requirements for Manipur pilot schemes.",
      checklistTitle: "Document Readiness Checklist",
      checklistDesc: "Manage required documents per scheme offline. Marks persist on this device and are never uploaded.",
      lblSelectScheme: "Select Scholarship Scheme",
      haveCount: "Have",
      missingCount: "Missing",
      unknownCount: "Unknown",
      btnHave: "HAVE",
      btnMissing: "MISSING",
      btnUnknown: "UNKNOWN",
      npciTitle: "Mandatory NPCI APB Mapping Requirement",
      npciWarning: "Standard bank account KYC is insufficient. Your Aadhaar number must be actively linked to your bank account and mapped on the NPCI Aadhaar Payment Bridge (APB) mapper for PFMS DBT scholarship disbursement.",
      otrTitle: "NSP One-Time Registration (OTR) Face RD",
      otrWarning: "National Scholarship Portal 2.0 requires One-Time Registration with Aadhaar Face RD biometric verification prior to application submission.",
      btnClearData: "Clear My Data",
      dataClearedToast: "All local data (profile, checklist marks, chat history) has been cleared from this device.",
      offlineNotice: "You are offline. Cached checklist and app shell remain fully functional.",
      errorGeneric: "An error occurred. Please try again.",
      errorOllamaDown: "The local Ollama language service is currently unreachable. SchemeSaathi operates under a strict fail-closed policy to prevent hallucination.",
      btnRetry: "Retry",
      closedWindowNotice: "Academic Year 2024–2025 (Application Window Closed)",
    },
    mni: {
      appName: "SchemeSaathi",
      appSubtitle: "Bharatki Scholarship Thiheibagi Platform",
      pilotBanner: "Demo — Manipur Pilot. Prototype build-ni, miyamgidamak puthorakpa natte.",
      tabEligibility: "Eligibility Yengba",
      tabChat: "SchemeSaathi-da Hangba",
      tabChecklist: "Eigi Document-sing",
      eligibilityTitle: "Statutory Eligibility Yengba",
      eligibilityDesc: "Government guideline-da yumfam ouraga deterministic rule-na yengba. Pilot scheme 6 mak AY 2024-2025 gi window thingkhraba ngaktani.",
      lblDomicile: "Leikhibagi State (Domicile)",
      lblCategory: "Social Category (Caste/Tribe)",
      lblIncome: "Chahigi Imunggi Senfam (₹)",
      lblCourse: "Tamlibagi Thaki (Course Level)",
      lblMarks: "Hanna Fangkhiba Marks (%)",
      lblGender: "Nupa/Nupi (Gender)",
      lblDisplaced: "Khudongchadaba/Displaced Oiraba Mahiroi (Manipur)",
      btnEvaluate: "Statutory Eligibility Yengba",
      evaluating: "Deterministic Rule-sing Yenglari...",
      chatTitle: "Grounded Conversational Assistant",
      chatDesc: "Paokhum pumnamak official document chunk-ta yumfam oi. Eligibility-di engine khaktana khenjilli.",
      chatPlaceholder: "Scholarship-ki niyam, senfam, deadline-gi maramda hangbiyu...",
      btnSend: "Thabiyu",
      loadingOllama: "Official guideline Ollama (llama3.2:3b) da yenglari...",
      chatWelcome: "Khurumjari! Eidi SchemeSaathi-ni. Manipur pilot scheme-singgi eligibility niyam, senfam, nattraga document-gi maramda hangbiu.",
      checklistTitle: "Document Sem-saba Yengba",
      checklistDesc: "Scheme khudingmakki document offline amadi device asida thambiyu. Server-da karigumba upload touramloi.",
      lblSelectScheme: "Scholarship Scheme Khanbiyu",
      haveCount: "Lei",
      missingCount: "Leite",
      unknownCount: "Khangde",
      btnHave: "LEI",
      btnMissing: "LEITE",
      btnUnknown: "KHANGDE",
      npciTitle: "NPCI APB Mapping Taba Tangai",
      npciWarning: "Bank account KYC khaktana matik charamloi. Aadhaar number-do bank account ga link touduna NPCI Aadhaar Payment Bridge (APB) mapper-da actively map touba tangai, adu oirabadi PFMS DBT sen tharakpada thengnaroi.",
      otrTitle: "NSP One-Time Registration (OTR) Face RD",
      otrWarning: "National Scholarship Portal 2.0 da application submit toudringei mamangda Aadhaar Face RD biometric verification touduna One-Time Registration (OTR) touba tangai.",
      btnClearData: "Eigi Data Mutthatpu",
      dataClearedToast: "Pumnamak local data (profile, checklist marks, chat history) device asidagi mutthatkhre.",
      offlineNotice: "Device asi offline oiri. Checklist amadi app shell asi matik chana touri.",
      errorGeneric: "Asengba afaba fangkhide. Amuk hanna hotnabiyu.",
      errorOllamaDown: "Local Ollama service asi louthokpa ngamde. SchemeSaathi-na hallucination thingnabagidamak fail-closed policy chathari.",
      btnRetry: "Amuk Hanna Hotnou",
      closedWindowNotice: "Academic Year 2024–2025 (Application Window Thingkhre)",
    },
  };

  let currentLang = localStorage.getItem("schemesaathi_lang") || "en";

  // --- 2. Pilot Schemes & Document Definitions ---
  const SCHEME_DOCUMENTS = {
    "SCH-MN-005": {
      title: "Post-Matric Scholarship for ST Students - Manipur",
      ay: "2024-2025",
      window_close: "2024-11-30",
      status: "CLOSED",
      portal_url: "https://tahmanipur.gov.in/",
      docs: [
        { id: "income_cert", name: "Income Certificate", desc: "Issued by competent authority, annual income ≤ ₹2.50 lakh" },
        { id: "caste_cert", name: "ST Certificate", desc: "Permanent Scheduled Tribe certificate issued by DC / SDO" },
        { id: "marksheet", name: "Previous Qualifying Marksheet", desc: "Marksheet of Class 10 / 12 / Bachelor degree" },
        { id: "prc", name: "Permanent Residential Certificate (PRC)", desc: "Proof of permanent domicile in Manipur" },
        { id: "admission_proof", name: "College ID / Admission Slip", desc: "Bonafide student proof from recognized institution" },
        { id: "apb_proof", name: "NPCI Aadhaar Payment Bridge (APB) Seeding", desc: "Bank account linked with Aadhaar and mapped on NPCI" },
      ],
    },
    "SCH-MN-001": {
      title: "Post-Matric Scholarship for SC Students - Manipur",
      ay: "2024-2025",
      window_close: "2024-11-30",
      status: "CLOSED",
      portal_url: "https://manipurobcsc.mn.gov.in/",
      docs: [
        { id: "income_cert", name: "Income Certificate", desc: "Issued by competent authority, annual income ≤ ₹2.50 lakh" },
        { id: "caste_cert", name: "SC Caste Certificate", desc: "Official SC certificate issued by competent authority" },
        { id: "marksheet", name: "Previous Exam Marksheet", desc: "Qualifying marksheet for matriculation / higher studies" },
        { id: "prc", name: "Manipur Domicile Certificate", desc: "Valid permanent residential proof" },
        { id: "admission_proof", name: "College Admission Proof", desc: "Receipt or college identity card" },
        { id: "apb_proof", name: "NPCI Aadhaar Payment Bridge (APB) Seeding", desc: "Bank account linked with Aadhaar on NPCI mapper" },
      ],
    },
    "SCH-MN-003": {
      title: "Chief Minister's College Students Rehabilitation Scheme (Displaced Students)",
      ay: "2024-2025",
      window_close: "2025-03-31",
      status: "CLOSED",
      portal_url: "https://highereducation.mn.gov.in/",
      docs: [
        { id: "displaced_cert", name: "Displaced Student Certificate", desc: "Issued by Relief Camp In-charge / DC / SDO Manipur" },
        { id: "college_id", name: "College Identity / Admission Proof", desc: "Enrolled in Government or Aided College in Manipur" },
        { id: "marksheet", name: "Previous Academic Record", desc: "Marksheet of qualifying class" },
        { id: "apb_proof", name: "Aadhaar Bank APB Seeding Confirmation", desc: "For direct financial aid disbursement" },
      ],
    },
    "SCH-MN-004": {
      title: "Pre-Matric Scholarship for ST Students (Class IX & X) - Manipur",
      ay: "2024-2025",
      window_close: "2024-11-30",
      status: "CLOSED",
      portal_url: "https://tahmanipur.gov.in/",
      docs: [
        { id: "income_cert", name: "Income Certificate", desc: "Family income ≤ ₹2.50 lakh" },
        { id: "caste_cert", name: "ST Tribe Certificate", desc: "Official ST certificate" },
        { id: "school_id", name: "Class IX or X Bonafide Certificate", desc: "Issued by Head of School" },
        { id: "prc", name: "Domicile Certificate", desc: "Proof of Manipur residency" },
      ],
    },
    "SCH-MN-002": {
      title: "Pre-Matric Scholarship for SC Students (Class IX & X) - Manipur",
      ay: "2024-2025",
      window_close: "2024-11-30",
      status: "CLOSED",
      portal_url: "https://manipurobcsc.mn.gov.in/",
      docs: [
        { id: "income_cert", name: "Income Certificate", desc: "Family income ≤ ₹2.50 lakh" },
        { id: "caste_cert", name: "SC Certificate", desc: "Official SC caste certificate" },
        { id: "school_id", name: "School Bonafide Certificate", desc: "Enrolled in Class 9 or 10" },
      ],
    },
    "SCH-MN-006": {
      title: "Financial Support to Students of NER (NEC Merit Scholarship)",
      ay: "2024-2025",
      window_close: "2024-10-31",
      status: "CLOSED",
      portal_url: "https://scholarships.gov.in/",
      docs: [
        { id: "prc", name: "Permanent Resident Certificate (PRC)", desc: "Proof of domicile in any NER state (Manipur, Assam, etc.)" },
        { id: "marksheet", name: "Qualifying Marksheet (≥60% marks)", desc: "HSLC / HSSLC / Degree marksheet with min 60%" },
        { id: "admission_proof", name: "Higher Professional Course Admission Proof", desc: "Diploma / Degree / PG in recognized institute" },
        { id: "income_cert", name: "Family Income Certificate", desc: "Annual income ≤ ₹8.00 lakh" },
      ],
    },
  };

  // --- 3. Client-Side Aadhaar Scrubbing ---
  function redactAadhaarClientSide(text) {
    if (!text || typeof text !== "string") return text;
    // Redact 12-digit number sequences (with or without spaces/dashes)
    return text
      .replace(/\b\d{4}[-\s]?\d{4}[-\s]?\d{4}\b/g, "[AADHAAR REDACTED]")
      .replace(/\b\d{12}\b/g, "[AADHAAR REDACTED]");
  }

  // --- 4. IndexedDB Offline Storage Helper ---
  const DB_NAME = "schemesaathi_pwa";
  const DB_VERSION = 1;
  const STORE_NAME = "checklist_store";

  function openIndexedDb() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);
      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve(request.result);
      request.onupgradeneeded = (e) => {
        const db = e.target.result;
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          db.createObjectStore(STORE_NAME, { keyPath: "scheme_id" });
        }
      };
    });
  }

  async function getStoredChecklist(schemeId) {
    try {
      const db = await openIndexedDb();
      return new Promise((resolve) => {
        const tx = db.transaction(STORE_NAME, "readonly");
        const store = tx.objectStore(STORE_NAME);
        const req = store.get(schemeId);
        req.onsuccess = () => resolve(req.result ? req.result.marks : {});
        req.onerror = () => resolve({});
      });
    } catch (_e) {
      return {};
    }
  }

  async function saveStoredChecklist(schemeId, marks) {
    try {
      const db = await openIndexedDb();
      return new Promise((resolve, reject) => {
        const tx = db.transaction(STORE_NAME, "readwrite");
        const store = tx.objectStore(STORE_NAME);
        store.put({
          scheme_id: schemeId,
          marks: marks,
          updated_at: new Date().toISOString(),
        });
        tx.oncomplete = () => resolve(true);
        tx.onerror = () => reject(tx.error);
      });
    } catch (_e) {
      return false;
    }
  }

  async function clearAllIndexedDb() {
    try {
      const db = await openIndexedDb();
      return new Promise((resolve, reject) => {
        const tx = db.transaction(STORE_NAME, "readwrite");
        const store = tx.objectStore(STORE_NAME);
        store.clear();
        tx.oncomplete = () => resolve(true);
        tx.onerror = () => reject(tx.error);
      });
    } catch (_e) {
      return false;
    }
  }

  // --- 5. Language Switching ---
  function applyLanguage(lang) {
    currentLang = lang;
    localStorage.setItem("schemesaathi_lang", lang);
    const dict = I18N[lang] || I18N.en;

    document.querySelectorAll("[data-i18n]").forEach((el) => {
      const key = el.getAttribute("data-i18n");
      if (dict[key]) {
        el.textContent = dict[key];
      }
    });

    document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
      const key = el.getAttribute("data-i18n-placeholder");
      if (dict[key]) {
        el.placeholder = dict[key];
      }
    });

    const langToggleBtn = document.getElementById("lang-toggle");
    if (langToggleBtn) {
      langToggleBtn.textContent = lang === "en" ? "MNI (Meiteilon)" : "EN (English)";
    }
  }

  // --- 6. Tab Navigation ---
  function initTabs() {
    const tabButtons = document.querySelectorAll(".tab-btn");
    const views = document.querySelectorAll(".view-pane");

    tabButtons.forEach((btn) => {
      btn.addEventListener("click", () => {
        const targetViewId = btn.getAttribute("data-tab");

        tabButtons.forEach((b) => {
          b.classList.remove("active");
          b.setAttribute("aria-selected", "false");
        });
        views.forEach((v) => {
          v.style.display = "none";
          v.setAttribute("hidden", "true");
        });

        btn.classList.add("active");
        btn.setAttribute("aria-selected", "true");
        const targetView = document.getElementById(targetViewId);
        if (targetView) {
          targetView.style.display = "block";
          targetView.removeAttribute("hidden");
        }
      });
    });
  }

  // --- 7. View 1: Eligibility Evaluation Flow ---
  function initEligibilityFlow() {
    const form = document.getElementById("eligibility-form");
    const submitBtn = document.getElementById("eval-submit-btn");
    const resultsArea = document.getElementById("eval-results-area");
    const resultsList = document.getElementById("eval-results-list");
    const timeMsSpan = document.getElementById("eval-time-ms");
    const countsSpan = document.getElementById("eval-counts-summary");

    if (!form) return;

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const dict = I18N[currentLang] || I18N.en;
      submitBtn.disabled = true;
      submitBtn.textContent = dict.evaluating;

      const payload = {};
      const domicile = document.getElementById("domicile_state").value.trim();
      if (domicile) payload.domicile_state = redactAadhaarClientSide(domicile);

      const category = document.getElementById("social_category").value;
      if (category) payload.social_category = category;

      const income = document.getElementById("annual_family_income_inr").value;
      if (income !== "") payload.annual_family_income_inr = parseFloat(income);

      const course = document.getElementById("course_level").value;
      if (course) payload.course_level = course;

      const marks = document.getElementById("marks_percent").value;
      if (marks !== "") payload.marks_percent = parseFloat(marks);

      const gender = document.getElementById("gender").value;
      if (gender) payload.gender = gender;

      payload.is_displaced = document.getElementById("is_displaced").checked;

      try {
        const res = await fetch("/api/v1/eligibility/evaluate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          showToast(errData.detail || errData.message || dict.errorGeneric);
          return;
        }

        const data = await res.json();
        renderEligibilityResults(data);
      } catch (err) {
        showToast(dict.offlineNotice + " (" + err.message + ")");
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = dict.btnEvaluate;
      }
    });

    function renderEligibilityResults(data) {
      resultsArea.style.display = "block";
      timeMsSpan.textContent = data.execution_duration_ms;
      countsSpan.innerHTML = `<strong>${data.total_eligible}</strong> Eligible &bull; <strong>${data.total_not_eligible}</strong> Not Eligible &bull; <strong>${data.total_unknown}</strong> Unknown`;

      resultsList.innerHTML = "";
      if (!data.schemes || data.schemes.length === 0) {
        resultsList.innerHTML = '<div class="card">No schemes evaluated.</div>';
        return;
      }

      data.schemes.forEach((sch) => {
        const card = document.createElement("div");
        card.className = `scheme-card ${sch.overall_outcome}`;

        const badgeClass = `badge-${sch.overall_outcome}`;
        const badgeLabel = sch.overall_outcome.replace("_", " ");

        // Retrieve known scheme window dates or fallback
        const meta = SCHEME_DOCUMENTS[sch.scheme_id] || {
          ay: "2024-2025",
          window_close: "2024-11-30",
          status: "CLOSED",
          portal_url: sch.official_source_url,
        };

        let diagHtml = "";
        if (sch.diagnostics && sch.diagnostics.length > 0) {
          diagHtml = sch.diagnostics
            .map((d) => {
              const icon = d.outcome === "PASS" ? "&#10003;" : d.outcome === "FAIL" ? "&#10007;" : "?";
              return `<div class="diag-item">
                <span class="diag-icon ${d.outcome}">${icon}</span>
                <div><strong>${d.clause_name}:</strong> ${d.explanation_en}</div>
              </div>`;
            })
            .join("");
        }

        let ineligHtml = "";
        if (sch.ineligibility_reasons && sch.ineligibility_reasons.length > 0) {
          ineligHtml = `<div style="margin-top:0.35rem; color:#b91c1c; font-size:0.8rem;">
            <strong>Reasons:</strong> ${sch.ineligibility_reasons.join("; ")}
          </div>`;
        }

        card.innerHTML = `
          <div class="scheme-header">
            <div class="scheme-title">${sch.scheme_title}</div>
            <span class="badge ${badgeClass}">${badgeLabel}</span>
          </div>
          <div class="scheme-meta">
            <span><strong>Scheme ID:</strong> ${sch.scheme_id}</span>
            <span><strong>Academic Year:</strong> ${meta.ay}</span>
            <span class="window-badge">Window Closed: ${meta.window_close} (CLOSED)</span>
          </div>
          <div class="diag-list">${diagHtml}</div>
          ${ineligHtml}
          <div>
            <a href="${sch.official_source_url}" target="_blank" rel="noopener noreferrer" class="portal-link">
              Official Portal Guidelines &rarr;
            </a>
          </div>
        `;
        resultsList.appendChild(card);
      });
    }
  }

  // --- 8. View 2: Grounded Chat Flow ---
  function initChatFlow() {
    const chatForm = document.getElementById("chat-form");
    const chatInput = document.getElementById("chat-input");
    const chatMessages = document.getElementById("chat-messages");
    const chatSendBtn = document.getElementById("chat-send-btn");
    const chatErrorBanner = document.getElementById("chat-error-banner");
    const chatErrorText = document.getElementById("chat-error-text");
    const chatRetryBtn = document.getElementById("chat-retry-btn");

    if (!chatForm) return;

    let sessionId = "pwa-session-" + Math.random().toString(36).substring(2, 10);
    let lastQuery = "";

    chatForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const rawText = chatInput.value.trim();
      if (!rawText) return;

      const cleanText = redactAadhaarClientSide(rawText);
      chatInput.value = "";
      lastQuery = cleanText;

      appendUserBubble(cleanText);
      await sendChatMessage(cleanText);
    });

    if (chatRetryBtn) {
      chatRetryBtn.addEventListener("click", async () => {
        chatErrorBanner.style.display = "none";
        if (lastQuery) {
          await sendChatMessage(lastQuery);
        }
      });
    }

    async function sendChatMessage(message) {
      const dict = I18N[currentLang] || I18N.en;
      chatErrorBanner.style.display = "none";
      chatSendBtn.disabled = true;

      const loadingId = appendLoadingBubble(dict.loadingOllama);

      try {
        const res = await fetch("/api/v1/chat/message", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id: sessionId,
            message: message,
          }),
        });

        removeBubble(loadingId);

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          const isOllamaError =
            res.status >= 500 ||
            (errData.detail && errData.detail.toLowerCase().includes("ollama"));

          chatErrorText.textContent = isOllamaError
            ? dict.errorOllamaDown
            : errData.detail || errData.message || dict.errorGeneric;
          chatErrorBanner.style.display = "flex";
          return;
        }

        const data = await res.json();
        appendAssistantBubble(data);
      } catch (err) {
        removeBubble(loadingId);
        chatErrorText.textContent = dict.errorOllamaDown + " (" + err.message + ")";
        chatErrorBanner.style.display = "flex";
      } finally {
        chatSendBtn.disabled = false;
      }
    }

    function appendUserBubble(text) {
      const bubble = document.createElement("div");
      bubble.className = "chat-bubble user";
      bubble.textContent = text;
      chatMessages.appendChild(bubble);
      chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function appendLoadingBubble(text) {
      const id = "loading-" + Date.now();
      const bubble = document.createElement("div");
      bubble.id = id;
      bubble.className = "chat-bubble assistant";
      bubble.innerHTML = `<div class="loading-indicator"><div class="spinner"></div><span>${text}</span></div>`;
      chatMessages.appendChild(bubble);
      chatMessages.scrollTop = chatMessages.scrollHeight;
      return id;
    }

    function removeBubble(id) {
      const el = document.getElementById(id);
      if (el) el.remove();
    }

    function appendAssistantBubble(data) {
      const bubble = document.createElement("div");
      bubble.className = "chat-bubble assistant";

      // Build citation map
      const citationMap = {};
      (data.citations || []).forEach((c) => {
        citationMap[c.citation_num] = c;
      });

      // Format prose with clickable citation links
      let formattedText = data.answer.replace(/\[\^(\d+)\]/g, (match, p1) => {
        const num = parseInt(p1, 10);
        const c = citationMap[num];
        if (c && c.source_url) {
          return ` <a href="${c.source_url}" target="_blank" rel="noopener noreferrer" class="citation-link" title="${c.scheme_id}: ${c.section_title} (AY ${c.academic_year || '2024-2025'}, Closed: ${c.window_close_date || '2024-11-30'})">[${num}]</a>`;
        }
        return ` [^${num}]`;
      });

      let contentHtml = `<div>${formattedText}</div>`;

      // Separate labelled deterministic eligibility block if present
      if (
        data.eligibility_evaluation &&
        data.eligibility_evaluation.schemes &&
        data.eligibility_evaluation.schemes.length > 0
      ) {
        const eligItems = data.eligibility_evaluation.schemes
          .map((sch) => {
            const outcomeClass =
              sch.overall_outcome === "ELIGIBLE"
                ? "color:#059669;"
                : sch.overall_outcome === "NOT_ELIGIBLE"
                ? "color:#dc2626;"
                : "color:#d97706;";
            return `<div style="margin-bottom:0.25rem;">
              <strong>${sch.scheme_title}:</strong>
              <span style="${outcomeClass} font-weight:700;"> ${sch.overall_outcome}</span>
            </div>`;
          })
          .join("");

        contentHtml += `
          <div class="eligibility-box">
            <h4>Deterministic Eligibility Evaluation (AST Engine)</h4>
            ${eligItems}
          </div>
        `;
      }

      // Render citation provenance pills
      if (data.citations && data.citations.length > 0) {
        const pillsHtml = data.citations
          .map((c) => {
            return `<span class="citation-pill">
              <strong>[${c.citation_num}]</strong>
              <a href="${c.source_url}" target="_blank" rel="noopener noreferrer">${c.scheme_id}</a>
              &bull; AY ${c.academic_year || "2024-2025"} &bull; Closed: ${c.window_close_date || "2024-11-30"}
            </span>`;
          })
          .join("");

        contentHtml += `<div class="citations-panel">${pillsHtml}</div>`;
      }

      bubble.innerHTML = contentHtml;
      chatMessages.appendChild(bubble);
      chatMessages.scrollTop = chatMessages.scrollHeight;
    }
  }

  // --- 9. View 3: Offline Document Checklist ---
  async function initChecklistFlow() {
    const select = document.getElementById("checklist-scheme-select");
    const container = document.getElementById("checklist-container");
    const counter = document.getElementById("checklist-counter");

    if (!select || !container) return;

    // Populate schemes in dropdown
    select.innerHTML = "";
    Object.keys(SCHEME_DOCUMENTS).forEach((schemeId) => {
      const opt = document.createElement("option");
      opt.value = schemeId;
      opt.textContent = `${schemeId} — ${SCHEME_DOCUMENTS[schemeId].title}`;
      select.appendChild(opt);
    });

    let activeSchemeId = select.value || "SCH-MN-005";
    await renderChecklist(activeSchemeId);

    select.addEventListener("change", async () => {
      activeSchemeId = select.value;
      await renderChecklist(activeSchemeId);
    });

    async function renderChecklist(schemeId) {
      const scheme = SCHEME_DOCUMENTS[schemeId];
      if (!scheme) return;

      const storedMarks = await getStoredChecklist(schemeId);

      container.innerHTML = "";

      let haveCount = 0;
      let missingCount = 0;
      let unknownCount = 0;

      scheme.docs.forEach((doc) => {
        const currentStatus = storedMarks[doc.id] || "UNKNOWN";
        if (currentStatus === "HAVE") haveCount++;
        else if (currentStatus === "MISSING") missingCount++;
        else unknownCount++;

        const itemDiv = document.createElement("div");
        itemDiv.className = "checklist-item";

        itemDiv.innerHTML = `
          <div class="item-info">
            <div class="item-name">${doc.name}</div>
            <div class="item-desc">${doc.desc}</div>
          </div>
          <div class="status-toggles" role="group" aria-label="Document status for ${doc.name}">
            <button class="toggle-btn HAVE ${currentStatus === "HAVE" ? "active" : ""}" data-doc="${doc.id}" data-status="HAVE">HAVE</button>
            <button class="toggle-btn MISSING ${currentStatus === "MISSING" ? "active" : ""}" data-doc="${doc.id}" data-status="MISSING">MISSING</button>
            <button class="toggle-btn UNKNOWN ${currentStatus === "UNKNOWN" ? "active" : ""}" data-doc="${doc.id}" data-status="UNKNOWN">UNKNOWN</button>
          </div>
        `;

        // Attach toggle listeners
        itemDiv.querySelectorAll(".toggle-btn").forEach((btn) => {
          btn.addEventListener("click", async () => {
            const docId = btn.getAttribute("data-doc");
            const newStatus = btn.getAttribute("data-status");
            storedMarks[docId] = newStatus;
            await saveStoredChecklist(schemeId, storedMarks);
            await renderChecklist(schemeId);
          });
        });

        container.appendChild(itemDiv);
      });

      const dict = I18N[currentLang] || I18N.en;
      counter.textContent = `${haveCount} ${dict.haveCount} • ${missingCount} ${dict.missingCount} • ${unknownCount} ${dict.unknownCount}`;
    }
  }

  // --- 10. Clear My Data Action ---
  function initClearData() {
    const clearBtn = document.getElementById("clear-data-btn");
    if (!clearBtn) return;

    clearBtn.addEventListener("click", async () => {
      const confirmed = window.confirm(
        "Are you sure you want to delete all saved profile facts, checklist marks, and chat history from this device?"
      );
      if (!confirmed) return;

      await clearAllIndexedDb();
      localStorage.removeItem("schemesaathi_profile");
      localStorage.removeItem("schemesaathi_chat");

      // Reset forms
      const eligForm = document.getElementById("eligibility-form");
      if (eligForm) eligForm.reset();

      const resultsArea = document.getElementById("eval-results-area");
      if (resultsArea) resultsArea.style.display = "none";

      const chatMessages = document.getElementById("chat-messages");
      if (chatMessages) {
        const dict = I18N[currentLang] || I18N.en;
        chatMessages.innerHTML = `<div class="chat-bubble assistant">${dict.chatWelcome}</div>`;
      }

      // Re-render checklist
      const select = document.getElementById("checklist-scheme-select");
      if (select) {
        select.dispatchEvent(new Event("change"));
      }

      const dict = I18N[currentLang] || I18N.en;
      showToast(dict.dataClearedToast);
    });
  }

  // --- 11. Toast Notifications ---
  function showToast(message) {
    let toast = document.getElementById("app-toast");
    if (!toast) {
      toast = document.createElement("div");
      toast.id = "app-toast";
      toast.className = "toast";
      document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.style.display = "block";
    setTimeout(() => {
      toast.style.display = "none";
    }, 4000);
  }

  // --- 12. PWA Service Worker Registration ---
  function registerServiceWorker() {
    if ("serviceWorker" in navigator) {
      window.addEventListener("load", () => {
        navigator.serviceWorker
          .register("/sw.js", { scope: "/" })
          .then((_reg) => {
            // Service worker successfully registered
          })
          .catch((_err) => {
            // Offline or SW failed
          });
      });
    }
  }

  // --- 13. Initialization ---
  document.addEventListener("DOMContentLoaded", () => {
    initTabs();
    initEligibilityFlow();
    initChatFlow();
    initChecklistFlow();
    initClearData();
    registerServiceWorker();

    // Language toggle button listener
    const langBtn = document.getElementById("lang-toggle");
    if (langBtn) {
      langBtn.addEventListener("click", () => {
        const nextLang = currentLang === "en" ? "mni" : "en";
        applyLanguage(nextLang);
        // Refresh checklist counters
        const select = document.getElementById("checklist-scheme-select");
        if (select) select.dispatchEvent(new Event("change"));
      });
    }

    applyLanguage(currentLang);
  });
})();
