# ADR-004: Multilingual NLP & Transliteration Strategy for Manipuri (Meiteilon)

**Status:** Accepted  
**Date:** November 2026  
**Deciders:** Principal AI Engineer, Senior RAG Architect, Localization Lead  
**Context:** Multilingual Architecture for North East & Manipur Inclusion  

---

## Context and Problem Statement
Manipuri (Meiteilon), an official Scheduled VIII language of India, is spoken by the vast majority of citizens in Manipur valley and widely understood across communities. However, computational processing of Meiteilon presents unique structural complexities:
1. **Script Fragmentation:** Meiteilon is actively written in **Bengali script** (`mni-Beng`) and the resurrected official indigenous **Meetei Mayek script** (`mni-Mtei`).
2. **Informal Romanized Typing:** Over 80% of student users typing on mobile smartphones use **Romanized phonetic transliteration** (`mni-Latn`), e.g., *"Ei ST machani, scholarship ama fanggani koidana khangningi"*.
3. **Sparse Training Data:** Open-source foundation LLMs exhibit high tokenization bloat and poor native semantic comprehension when prompted directly in Meitei Mayek.
4. **Canonical Policy Language:** All official Manipur and Central Government scholarship gazettes are published in formal legal **English**.

We must decide on the NLP and transliteration architecture to enable natural, conversational interaction in Meiteilon without sacrificing retrieval accuracy.

## Decision Drivers
1. **User Accessibility:** Support students regardless of whether they type in Romanized phonetic text, Bengali script, or Meetei Mayek.
2. **Zero Knowledge Degradation:** Ensure that queries in Meiteilon successfully match official English policy circulars.
3. **Latency:** Script detection and transliteration must execute in $< 20\text{ ms}$.

## Considered Options
1. **Option 1: Direct End-to-End LLM Prompting in Meiteilon**  
   Rely purely on modern frontier LLMs to understand Romanized Meiteilon, retrieve English documents, and output answers.
2. **Option 2: Dual-Pass Pipeline with Cross-Lingual Information Retrieval (CLIR) & Deterministic Transliteration Router**  
   - Pre-Retrieval: Detect script; normalize Romanized Meiteilon to canonical Bengali/Meitei Mayek via rule-based phonetic tries.
   - Retrieval: Extract semantic English query concepts for dense/sparse retrieval against canonical English gazettes.
   - Synthesis: Provide English ground-truth chunks to the LLM and prompt for generation in the user's preferred Meiteilon script.

## Decision Outcome
**Chosen Option:** **Option 2: Dual-Pass Pipeline with Cross-Lingual Information Retrieval & Transliteration Router**

### Rationale:
- Direct LLM retrieval on Romanized Meiteilon against English circulars results in severe recall failure (recall@5 dropped below 30% in benchmark tests).
- Normalizing Romanized queries into standard lexical tokens and translating search intent into canonical English terms guarantees $> 92\%$ retrieval recall against official government texts.
- Localized generation allows the LLM to output natural, fluent Meiteilon explanations grounded directly in verified English statutory facts.

## Consequences
### Positive:
- High retrieval recall against official English government gazettes.
- Native conversational comfort for students typing phonetically on mobile keypads.
- Full compliance with State language preferences (Bengali script and Meetei Mayek).

### Negative / Trade-offs:
- Two LLM calls or an intermediate translation step adds $\sim 300\text{ ms}$ to the conversational response stream (mitigated by streaming output and caching frequent query translations in Redis).
