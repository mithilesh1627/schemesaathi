# ADR-002: Deterministic Rule Engine Decoupled from Conversational RAG

**Status:** Accepted  
**Date:** November 2026  
**Deciders:** Principal AI Engineer, Senior RAG Architect  
**Context:** Reliability & Zero-Hallucination Design for Statutory Eligibility  

---

## Context and Problem Statement
Government scholarship eligibility is governed by strict, legally binding statutory criteria (income cutoffs, social categories, marks thresholds, course levels, board verifications). Generative LLMs, when tasked with directly determining whether an applicant qualifies, exhibit probabilistic drift: hallucinating eligibility for candidates exceeding income caps, confusing central and state caste categories, or ignoring closing dates.

We must decide whether to let the LLM evaluate eligibility directly from retrieved context chunks (Pure RAG) or decouple eligibility into a deterministic rule engine that runs prior to or alongside RAG.

## Decision Drivers
1. **Zero Tolerance for Hallucinated Eligibility:** False positives cause students to incur non-refundable application and cyber café fees, leading to downstream rejection by government verification officers.
2. **Legal Auditability:** Eligibility decisions must be 100% reproducible and explainable down to exact statutory clauses.
3. **Execution Speed:** Evaluating a student's profile across 50+ schemes must take $< 50\text{ ms}$.

## Considered Options
1. **Option 1: Pure LLM-Based Evaluation (Prompt-Engineered RAG)**  
   Feed the user profile and retrieved scheme guidelines into an LLM and prompt it to decide "Eligible / Ineligible".
2. **Option 2: Hybrid Pipeline with Deterministic Rule Engine Precedence**  
   Parse statutory rules into a JSON-Logic Abstract Syntax Tree (AST). The AST engine deterministically evaluates the user profile. The LLM's role is strictly restricted to conversational dialogue, slot-filling, translation, and explaining the deterministic outcome.

## Decision Outcome
**Chosen Option:** **Option 2: Hybrid Pipeline with Deterministic Rule Engine Precedence**

### Rationale:
- Abstract Syntax Trees execute mathematically via standard Boolean evaluation in $< 15\text{ ms}$ with zero risk of arithmetic or boundary errors.
- The LLM is provided with the *already computed* deterministic outcome as an immutable system constraint, preventing it from ever hallucinating an contrary verdict.
- Enables progressive profiling ("Missing 1 field: Enter your Class 12 percentage to verify PM-USP eligibility") via formal partial AST evaluation.

## Consequences
### Positive:
- 0.00% false positive rate on numerical, categorical, and temporal boundaries.
- Instantaneous, line-by-line diagnostic explanations (`passed_income_check: false`, `ceiling: 250000`, `actual: 320000`).
- Dramatically reduced token costs, since the LLM does not need to re-read and deliberate over dozens of long guideline documents.

### Negative / Trade-offs:
- Requires an ingestion step to convert raw policy PDFs into validated JSON-Logic AST expressions.
- Complex policy edge cases (e.g., nuanced discretionary exemptions) require human-in-the-loop verification before rule activation.
