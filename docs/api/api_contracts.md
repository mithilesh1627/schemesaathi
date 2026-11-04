# API Contracts & Integration Guide: SchemeSaathi

**Document Version:** 1.0.0  
**Status:** Milestone M0 Baseline Specification  
**Related OpenAPI File:** [`openapi_specification.yaml`](file:///D:/2026/schemesaathi/docs/api/openapi_specification.yaml)  
**Standard:** RESTful JSON / OpenAPI 3.1  

---

## 1. Overview & Architectural Principles

The SchemeSaathi API is designed to serve as a low-latency, stateless integration layer for web, mobile, and Common Service Centre (CSC) client applications.

### Key API Principles:
1. **Stateless Ephemeral Operation:** Evaluation endpoints (`/api/v1/eligibility/evaluate`) operate statelessly. Clients pass the profile payload and receive an instant mathematical evaluation without creating persistent accounts.
2. **Deterministic Explanations:** Responses do not simply state "Ineligible"; they return structured diagnostics containing exact clause justifications and alternative recommendations.
3. **Bandwidth Optimization:** Responses are structured to minimize JSON payload size ($< 15\text{ KB}$ uncompressed) to support 2G/3G connectivity in rural Manipur.

---

## 2. Core API Endpoints

### 2.1 Scheme Catalog (`GET /api/v1/schemes/catalog`)
Returns a filtered, paginated catalog of all officially verified central and state government scholarships.

#### Request Query Parameters:
- `category` (optional): Filter by social category (`ST`, `SC`, `OBC`, `GENERAL`).
- `domicile` (optional): Filter by state domicile (e.g., `MANIPUR`).
- `course_level` (optional): Filter by course tier (`UNDERGRADUATE`, `POSTGRADUATE`).
- `portal_status` (optional): `OPEN`, `CLOSED`, `UPCOMING`.
- `page` (default: 1), `limit` (default: 20).

#### Sample Response (200 OK):
```json
{
  "total": 44,
  "page": 1,
  "limit": 20,
  "schemes": [
    {
      "scheme_id": "sch-mn-005",
      "official_code": "MANIPUR_ST_POST_MATRIC",
      "title": {
        "en": "Post-Matric Scholarship for ST Students - Manipur",
        "mni_beng": "ꯃꯅꯤꯄꯨꯔꯒꯤ ST ꯃꯆꯥꯁꯤꯡꯒꯤ ꯄꯣꯁ꯭ꯠ-ꯃꯦꯠꯔꯤꯛ ꯁ꯭ꯀꯣꯂꯔꯁꯤꯞ"
      },
      "issuing_level": "CENTRALLY_SPONSORED",
      "ministry_or_department": "Department of Tribal Affairs & Hills, Manipur",
      "portal_status": "CLOSED",
      "income_ceiling_annual_inr": 250000
    }
  ]
}
```

---

### 2.2 Deterministic Eligibility Evaluation (`POST /api/v1/eligibility/evaluate`)
Executes an in-memory JSON-Logic AST evaluation across statutory rules.

#### Sample Request Body:
```json
{
  "session_id": "sess_ephem_98234",
  "demographics": {
    "social_category": "ST",
    "gender": "FEMALE",
    "domicile_state": "MANIPUR",
    "is_displaced_affected": true,
    "is_differently_abled": false
  },
  "financial": {
    "annual_family_income_inr": 220000,
    "income_certificate_authority": "SDO"
  },
  "academic": {
    "current_course_level": "UNDERGRADUATE",
    "current_course_year": 1,
    "previous_qualifying_marks_percent": 74.5,
    "qualifying_board": "COHSEM",
    "is_institution_in_ner": true,
    "is_distance_learning": false
  }
}
```

#### Sample Response (200 OK):
```json
{
  "total_checked": 44,
  "total_eligible": 4,
  "execution_time_ms": 7,
  "schemes_by_tier": {
    "eligible_now": [],
    "eligible_off_cycle": [
      {
        "scheme_id": "sch-mn-005",
        "scheme_title": "Post-Matric Scholarship for ST Students - Manipur",
        "status": "ELIGIBLE_OFF_CYCLE",
        "diagnostics": [
          {
            "clause": "Category Check",
            "passed": true,
            "explanation_en": "Matches required Scheduled Tribe (ST) category."
          },
          {
            "clause": "Income Ceiling",
            "passed": true,
            "explanation_en": "Family income (₹2,20,000) is within the statutory ₹2,50,000 limit."
          }
        ],
        "application_portal_status": {
          "portal": "NSP_2_0",
          "status": "CLOSED",
          "next_expected_window": "July 2025"
        }
      },
      {
        "scheme_id": "sch-ner-012",
        "scheme_title": "Ishan Uday Special Scholarship for NER",
        "status": "ELIGIBLE_OFF_CYCLE",
        "diagnostics": [
          {
            "clause": "NER Domicile & Schooling",
            "passed": true,
            "explanation_en": "Permanent resident of Manipur with Class 12 schooling completed in NER."
          }
        ]
      }
    ],
    "conditionally_eligible": [],
    "ineligible": [
      {
        "scheme_id": "sch-cen-017",
        "scheme_title": "Top Class Education for SC Students",
        "status": "INELIGIBLE",
        "diagnostics": [
          {
            "clause": "Category Check",
            "passed": false,
            "explanation_en": "Scheme is strictly reserved for SC students; applicant is ST."
          }
        ]
      }
    ]
  }
}
```

---

### 2.3 Conversational RAG Query (`POST /api/v1/chat/message`)
Provides multilingual conversational guidance with inline source citations.

#### Sample Request Body:
```json
{
  "session_id": "sess_ephem_98234",
  "message": "Can I get Ishan Uday if my college is in Delhi but I studied school in Imphal?",
  "language_preference": "en"
}
```

#### Sample Response (200 OK):
```json
{
  "session_id": "sess_ephem_98234",
  "response_text": "Yes, you remain eligible for the Ishan Uday Special Scholarship. Under UGC guidelines, while your Class 12 schooling must be completed from a recognized board within the North Eastern Region (NER), your undergraduate college can be located anywhere in India, provided it is a recognized institution featuring a valid AISHE code[^1].",
  "detected_language": "en",
  "citations": [
    {
      "citation_id": "cite_ugc_01",
      "source_title": "UGC Ishan Uday Operational Guidelines 2024-25",
      "source_url": "https://scholarships.gov.in/public/schemeGuidelines/UGC_IshanUday.pdf",
      "page_number": 3,
      "academic_year": "2024-2025"
    }
  ],
  "suggested_follow_up_questions": [
    "What is the family income limit for Ishan Uday?",
    "Can I receive both Ishan Uday and Post-Matric ST together?",
    "What documents do I need to prepare before NSP opens?"
  ]
}
```

---

### 2.4 Document Readiness Checklist (`POST /api/v1/documents/checklist`)
Generates a pre-submission checklist and alerts students to administrative traps (e.g. invalid revenue authorities or missing NPCI bank mapping).

#### Sample Response (200 OK):
```json
{
  "documents": [
    {
      "document_code": "INCOME_CERT",
      "name": "Income Certificate",
      "issuing_authority": "Sub-Divisional Officer (SDO) / Sub-Deputy Collector (SDC) / Tehsildar",
      "validity_note": "Must be issued after April 1, 2024 (valid for current financial year only).",
      "common_rejection_pitfall": "Certificates issued by local Village Authorities / Khullakpa are frequently rejected by District Nodal Officers (DNOs)."
    },
    {
      "document_code": "ST_CERT",
      "name": "Scheduled Tribe (ST) Certificate",
      "issuing_authority": "Deputy Commissioner (DC) or Sub-Divisional Magistrate (SDM)",
      "validity_note": "Permanent validity; must match name on Aadhaar letter-for-letter."
    }
  ],
  "npci_dbt_warning": {
    "is_critical": true,
    "guidance_text": "Ensure your bank account is mapped in the NPCI Aadhaar Payment Bridge (APB). Simply having an Aadhaar number linked during account opening does NOT guarantee DBT eligibility."
  },
  "otr_readiness_guide": {
    "requires_face_rd": true,
    "common_app_error": "Install UIDAI AadhaarFaceRD from Google Play Store. If Error 904 occurs, verify that your biometrics are unlocked on the UIDAI portal."
  }
}
```

---

## 3. Standard Error Contract

All error responses return a standardized RFC-7807 compatible error envelope:

```json
{
  "error_code": "ERR_VALIDATION_FAILED",
  "message": "The family income value provided cannot be negative.",
  "details": {
    "field": "financial.annual_family_income_inr",
    "value": -50000
  },
  "timestamp": "2026-11-04T09:30:15Z"
}
```

| HTTP Status | Error Code | Description |
| :--- | :--- | :--- |
| **400 Bad Request** | `ERR_MALFORMED_REQUEST` | Missing or syntactically invalid JSON payload. |
| **422 Unprocessable** | `ERR_VALIDATION_FAILED` | Semantic validation failure in demographic or academic slots. |
| **429 Too Many Req** | `ERR_RATE_LIMIT_EXCEEDED` | Request frequency exceeds allowed leaky bucket threshold. |
| **500 Server Error** | `ERR_INTERNAL_EVALUATION` | Unexpected exception inside the AST evaluator. |
