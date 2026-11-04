# Deterministic Eligibility Engine Architecture: SchemeSaathi

**Document Version:** 1.0.0  
**Status:** Milestone M0 Baseline Specification  
**Component:** `EligibilityEngineModule` (Core Deterministic Layer)  
**Standard:** JSON-Logic Abstract Syntax Tree (AST) Evaluator  

---

## 1. Why Pure LLMs Fail at Eligibility Decisions

A foundational architectural principle of SchemeSaathi is that **Large Language Models (LLMs) must NEVER make the final eligibility determination**. Empirical testing across commercial and open-weight models reveals critical failure modes when evaluating government criteria:

| Failure Mode | Pure LLM Behavior | Real-World Impact on Student | Deterministic AST Engine Guarantee |
| :--- | :--- | :--- | :--- |
| **Numeric Threshold Drift** | Evaluates ₹2,55,000 as "close enough" to ₹2,50,000 ceiling. | Student spends ₹500 on application fees; rejected instantly by PFMS. | Strict mathematical inequality ($\text{income} \le 250000$); zero drift. |
| **Category Hallucination** | Assumes Meitei OBC automatically qualifies for Central ST schemes. | Student's form is marked "Defective"; faces debarment for false claims. | Explicit set membership check against statutory state lists. |
| **Date & Window Blindness** | Tells a student to apply in March for a portal window that closed in October. | Student experiences severe distress and missed deadlines. | Strict comparison between `current_date` and `[window_open, window_close]`. |
| **Non-Reproducibility** | Same profile gets different eligibility answers depending on temperature or phrasing. | Lack of legal auditability; loss of citizen trust. | 100% deterministic, reproducible, testable Boolean result. |
| **Concurrent Benefit Omission** | Informs student they can claim both *Ishan Uday* and *Post-Matric ST*. | Government clawback; student forced to refund full disbursement with interest. | Enforces dual-benefit exclusivity trees. |

---

## 2. Theoretical Architecture: Two-Tier Evaluation Pipeline

To achieve sub-15ms evaluation latency across 50+ schemes while maintaining zero hallucinations, SchemeSaathi employs a **Two-Tier Evaluation Pipeline**:

```mermaid
flowchart TD
    Profile["Student Profile Payload<br/>(Category, Income, Domicile, Marks, Course, Gender)"]
    
    subgraph Tier 1: High-Speed Relational Pre-Filter (PostgreSQL B-Tree & GIN)
        DB_QUERY["SELECT version_id FROM scheme_eligibility_rules WHERE<br/>- (income_ceiling IS NULL OR income_ceiling >= :user_income)<br/>- target_categories ?| ARRAY[:user_category, 'ALL']<br/>- eligible_domiciles ?| ARRAY[:user_domicile, 'ALL_INDIA']<br/>- eligible_course_levels ? :user_course"]
    end

    subgraph Tier 2: In-Memory JSON-Logic AST Evaluation Engine
        AST_LOAD["Load JSON-Logic AST for Filtered Schemes"]
        EXEC["Execute AST Evaluator against Full Profile Context"]
        PARTIAL["Partial Evaluation Solver<br/>(Identify Missing Attributes if Incomplete)"]
        DIAG["Generate Human-Readable & Multilingual Diagnostic Clauses"]
    end

    subgraph Evaluation Outcome
        OUT1["ELIGIBLE_NOW (Portal Open)"]
        OUT2["ELIGIBLE_OFF_CYCLE (Portal Closed)"]
        OUT3["CONDITIONALLY_ELIGIBLE (Missing 1-2 inputs)"]
        OUT4["INELIGIBLE (Failed statutory threshold)"]
    end

    Profile --> DB_QUERY
    DB_QUERY -- Filters 80% out in <5ms --> AST_LOAD
    AST_LOAD --> EXEC --> PARTIAL --> DIAG
    DIAG --> OUT1 & OUT2 & OUT3 & OUT4
```

---

## 3. JSON-Logic AST Specification & Grammar

The engine represents statutory eligibility using the standardized [JSON-Logic](https://jsonlogic.com/) grammar, extended with domain-specific operators.

### 3.1 Standard Supported Evaluation Context

```typescript
interface ApplicantContext {
  demographics: {
    social_category: "GENERAL" | "SC" | "ST" | "OBC" | "EBC" | "DNT";
    minority_community?: "MUSLIM" | "CHRISTIAN" | "SIKH" | "BUDDHIST" | "JAIN" | "PARSI" | null;
    gender: "MALE" | "FEMALE" | "TRANSGENDER";
    domicile_state: string; // e.g. "MANIPUR"
    is_displaced_affected?: boolean;
    is_differently_abled: boolean;
    disability_percentage?: number; // e.g. 40
    is_single_girl_child?: boolean;
    is_orphan?: boolean;
    is_ward_of_beedi_cine_mine_worker?: boolean;
    is_ward_of_armed_forces_martyr?: boolean;
  };
  financial: {
    annual_family_income_inr: number;
    has_valid_income_certificate: boolean;
    income_certificate_authority?: "SDO" | "TEHSILDAR" | "DC" | "VILLAGE_AUTHORITY" | "OTHER";
    income_certificate_issue_date?: string; // ISO 8601
  };
  academic: {
    current_course_level: "PRE_MATRIC" | "SECONDARY" | "HIGHER_SECONDARY" | "DIPLOMA" | "UNDERGRADUATE" | "POSTGRADUATE" | "MPHIL_PHD";
    current_course_year: number; // 1, 2, 3, 4
    previous_qualifying_marks_percent: number; // e.g. 76.5
    qualifying_board?: "COHSEM" | "BSEM" | "CBSE" | "ICSE" | "NIOS" | "OTHER";
    institution_aishe_code?: string;
    is_institution_in_ner: boolean;
    is_distance_learning: boolean;
    is_management_quota: boolean;
  };
  portal_lifecycle: {
    current_date: string; // ISO 8601 (e.g. "2026-11-04")
  };
}
```

---

## 4. Concrete AST Implementations for Key Schemes

### Example 1: Post-Matric Scholarship for ST Students - Manipur (`SCH-MN-005`)
Statutory Rule:
1. Category must be `ST`.
2. Domicile state must be `MANIPUR`.
3. Annual family income must be $\le ₹2,50,000$.
4. Course level must be post-matric (`HIGHER_SECONDARY`, `DIPLOMA`, `UNDERGRADUATE`, `POSTGRADUATE`, `MPHIL_PHD`).
5. Course mode must NOT be distance learning without prior approval.

```json
{
  "and": [
    { "==": [{ "var": "demographics.social_category" }, "ST"] },
    { "==": [{ "var": "demographics.domicile_state" }, "MANIPUR"] },
    { "<=": [{ "var": "financial.annual_family_income_inr" }, 250000] },
    {
      "in": [
        { "var": "academic.current_course_level" },
        ["HIGHER_SECONDARY", "DIPLOMA", "UNDERGRADUATE", "POSTGRADUATE", "MPHIL_PHD"]
      ]
    },
    { "!": { "var": "academic.is_distance_learning" } }
  ]
}
```

### Example 2: Ishan Uday Special Scholarship for NER (`SCH-NER-012`)
Statutory Rule:
1. Domicile state must be one of the 8 NER states (`ARUNACHAL_PRADESH`, `ASSAM`, `MANIPUR`, `MEGHALAYA`, `MIZORAM`, `NAGALAND`, `SIKKIM`, `TRIPURA`).
2. Qualifying schooling must be located within NER (`academic.is_institution_in_ner == true`).
3. Must be enrolled in the **first year** of a regular Undergraduate degree program.
4. Annual family income must be $\le ₹4,50,000$.
5. Admission must NOT be via management quota or open/distance university.

```json
{
  "and": [
    {
      "in": [
        { "var": "demographics.domicile_state" },
        ["ARUNACHAL_PRADESH", "ASSAM", "MANIPUR", "MEGHALAYA", "MIZORAM", "NAGALAND", "SIKKIM", "TRIPURA"]
      ]
    },
    { "==": [{ "var": "academic.is_institution_in_ner" }, true] },
    { "==": [{ "var": "academic.current_course_level" }, "UNDERGRADUATE"] },
    { "==": [{ "var": "academic.current_course_year" }, 1] },
    { "<=": [{ "var": "financial.annual_family_income_inr" }, 450000] },
    { "!": { "var": "academic.is_distance_learning" } },
    { "!": { "var": "academic.is_management_quota" } }
  ]
}
```

### Example 3: AICTE Pragati Scholarship for Girl Students (`SCH-CEN-036`)
Statutory Rule:
1. Gender must be `FEMALE`.
2. Must be admitted to 1st year of Technical Degree (or 2nd year via lateral entry).
3. Annual family income must be $\le ₹8,00,000$.
4. Institution must be AICTE-approved.

```json
{
  "and": [
    { "==": [{ "var": "demographics.gender" }, "FEMALE"] },
    { "<=": [{ "var": "financial.annual_family_income_inr" }, 800000] },
    { "==": [{ "var": "academic.current_course_level" }, "UNDERGRADUATE"] },
    {
      "or": [
        { "==": [{ "var": "academic.current_course_year" }, 1] },
        { "==": [{ "var": "academic.is_lateral_entry" }, true] }
      ]
    }
  ]
}
```

---

## 5. Diagnostic Generation & Partial Evaluation

### 5.1 Diagnostic Clause Mapping
When an expression evaluates to `false`, the engine traverses the AST to locate the specific failing predicate and maps it to a structured diagnostic code and human-readable explanation:

| Failing Predicate | Diagnostic Code | Generated Explanation (English) | Generated Explanation (Meiteilon / Manipuri) |
| :--- | :--- | :--- | :--- |
| `income > ceiling` | `ERR_INCOME_EXCEEDED` | Family income (₹{actual}) exceeds the statutory limit of ₹{ceiling}. | ꯏꯃꯨꯡꯒꯤ ꯂꯥꯛꯊꯣꯛ (₹{actual}) ꯑꯁꯤ ꯂꯩꯉꯥꯛꯀꯤ ꯑꯌꯥꯕ ꯄꯤꯔꯤꯕ ₹{ceiling} ꯗꯒꯤ ꯍꯦꯟꯂꯤ। |
| `category != target` | `ERR_CATEGORY_MISMATCH` | This scheme is reserved for {target}; your profile indicates {actual}. | ꯁ꯭ꯀꯤꯝ ꯑꯁꯤ {target} ꯒꯤ ꯃꯆꯥꯁꯤꯡꯈꯛꯇꯗ ꯄꯤꯕꯅꯤ; ꯅꯍꯥꯛꯅ {actual} ꯅꯤ। |
| `domicile != NER` | `ERR_DOMICILE_RESTRICTION` | Applicant must be a permanent resident of an eligible North Eastern State. | ꯑꯦꯄ꯭ꯂꯤꯀꯦꯟ ꯑꯁꯤ ꯑꯋꯥꯡ-ꯅꯣꯡꯄꯣꯛ (NER) ꯔꯥꯖ꯭ꯌ ꯑꯃꯒꯤ ꯃꯤꯑꯣꯏ ꯑꯣꯏꯒꯗꯕꯅꯤ। |
| `marks < cutoff` | `ERR_ACADEMIC_CUTOFF` | Qualifying marks ({actual}%) fall below the minimum threshold ({cutoff}%). | ꯃꯥꯔꯛ ({actual}%) ꯑꯁꯤ ꯃꯆꯥꯡ ꯑꯣꯏꯕ ꯊꯥꯛ ({cutoff}%) ꯗꯒꯤ ꯍꯟꯊꯔꯤ। |

### 5.2 Partial Evaluation (Handling Incomplete User Profiles)
Users often ask questions before providing all details (e.g., *"Can I get a scholarship for B.Tech?"* without stating their income or caste).
- **The Partial Solver Algorithm:** The engine substitutes known variables into the AST and simplifies the tree.
- **Output:** If the simplified tree does not resolve to `true` or `false`, the engine outputs `CONDITIONALLY_ELIGIBLE` with a minimal list of **unbound variables**:
  ```json
  {
    "status": "CONDITIONALLY_ELIGIBLE",
    "unbound_variables": [
      {
        "field": "financial.annual_family_income_inr",
        "prompt_en": "What is your total annual family income?",
        "prompt_mni": "ꯅꯍꯥꯛꯀꯤ ꯏꯃꯨꯡꯒꯤ ꯆꯍꯤ ꯑꯃꯒꯤ ꯑꯄꯨꯟꯕ ꯂꯥꯛꯊꯣꯛ ꯀꯌꯥꯅꯣ?"
      },
      {
        "field": "demographics.social_category",
        "prompt_en": "Which social category do you belong to (General, SC, ST, or OBC)?",
        "prompt_mni": "ꯅꯍꯥꯛ ꯀꯔꯝꯕ ꯀꯦꯇꯦꯒꯣꯔꯤ (General, SC, ST, OBC) ꯗ ꯆꯜꯂꯤ?"
      }
    ]
  }
  ```
- This triggers the conversational agent to ask targeted slot-filling questions rather than overwhelming the student with a 20-field questionnaire.
