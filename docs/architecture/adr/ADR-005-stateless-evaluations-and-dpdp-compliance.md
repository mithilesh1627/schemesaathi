# ADR-005: Stateless Guest Evaluations & Zero-Aadhaar DPDP Compliance

**Status:** Accepted  
**Date:** November 2026  
**Deciders:** Principal AI Engineer, Security & Compliance Architect, Product Lead  
**Context:** Privacy Architecture under Digital Personal Data Protection Act 2023  

---

## Context and Problem Statement
SchemeSaathi processes sensitive socio-economic and educational attributes (caste, parental income, disability status, exam percentages). Under India's **Digital Personal Data Protection Act 2023 (DPDP Act 2023)** and UIDAI regulations, holding citizen PII without explicit statutory justification or enterprise-grade data trustee controls incurs severe legal liabilities. Furthermore, rural students in conflict-affected regions like Manipur are deeply hesitant to share identifiable credentials on unfamiliar web platforms.

We must decide the data persistence model for user evaluations and the architectural boundary regarding Aadhaar and banking identifiers.

## Decision Drivers
1. **DPDP Act 2023 Alignment:** Data minimization, purpose specification, and user right to erasure must be structural invariants, not afterthoughts.
2. **Citizen Trust & Frictionless Adoption:** Students must be able to discover scholarships without mandatory registration or OTP logins.
3. **Zero Aadhaar Liability:** Absolute compliance with Supreme Court of India directives and UIDAI circulars prohibiting private storage of 12-digit Aadhaar numbers.

## Considered Options
1. **Option 1: Mandatory User Profiles with Long-Term PII Storage**  
   Force students to create an account with mobile OTP, name, Aadhaar, and address before checking eligibility.
2. **Option 2: Stateless / Ephemeral Guest Evaluation by Default with Zero PII Retention**  
   Allow students to evaluate eligibility anonymously. Profile inputs are kept exclusively in volatile memory for the duration of the HTTP session and purged upon completion. Cryptographic salt-hashed IP logs are maintained solely for rate limiting and fraud audit.

## Decision Outcome
**Chosen Option:** **Option 2: Stateless / Ephemeral Guest Evaluation by Default with Zero PII Retention**

### Rationale:
- Eliminates 95% of data compliance risk: Since no names, phone numbers, raw IP addresses, or home addresses are persisted, data breach risk is structurally eliminated.
- Drastic reduction in user drop-off: Students can receive an instant eligibility report in under 60 seconds without creating accounts or waiting for SMS OTPs across congested cellular networks.
- Strict enforcement of Zero-Aadhaar storage: The platform never collects, accepts, or stores 12-digit Aadhaar numbers or biometric tokens.

## Consequences
### Positive:
- Immediate compliance with Section 6 (Consent) and Section 8 (Obligations of Data Fiduciary) of DPDP Act 2023.
- Maximum adoption velocity across rural and displaced communities.
- Significantly reduced database storage requirements and zero PII backup encryption overhead.

### Negative / Trade-offs:
- Users cannot retrieve their previous evaluation history if they switch browsers or clear cookies (mitigated by offering a one-click "Download PDF Dossier" feature before the session ends).
- Cross-session longitudinal tracking is impossible without explicit opt-in user accounts.
