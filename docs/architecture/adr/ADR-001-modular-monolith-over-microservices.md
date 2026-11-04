# ADR-001: Modular Monolith Architecture over Microservices

**Status:** Accepted  
**Date:** November 2026  
**Deciders:** Principal AI Engineer, Senior RAG Architect, Product Engineer  
**Context:** System Architecture for SchemeSaathi Discovery & Eligibility Platform  

---

## Context and Problem Statement
When designing the architecture for SchemeSaathi, a critical early decision was whether to adopt a distributed microservices architecture (e.g., separate microservices for Catalog, Ingestion, Eligibility Evaluation, RAG, and Audit) or a Modular Monolith. 

The platform must support high-concurrency evaluation during peak scholarship submission windows (August–October), maintain sub-150ms evaluation latency, and remain operationally simple for small civic-tech engineering teams operating on limited public-good budgets.

## Decision Drivers
1. **Low Operational Overhead:** The platform must be deployable, maintainable, and monitorable without requiring dedicated DevOps or Kubernetes cluster engineering.
2. **Sub-15ms Rule Evaluation:** Cross-service network calls (HTTP/gRPC) add serialization and latency overhead that degrades multi-turn chat performance.
3. **Transaction Integrity:** Ensuring scheme catalog versions, AST rules, and knowledge embeddings remain synchronized during updates.
4. **Budget Constraints:** Target infrastructure cost must remain under $150/month.

## Considered Options
1. **Option 1: Distributed Microservices** (5 independent containerized services with gRPC/Kafka).
2. **Option 2: Unstructured Monolith** (Single codebase with mixed concerns and shared database models).
3. **Option 3: Domain-Driven Modular Monolith** (Single deployable container, strict internal bounded contexts, clean architecture, typed internal facades).

## Decision Outcome
**Chosen Option:** **Option 3: Domain-Driven Modular Monolith**

### Rationale:
- Bounded contexts (`SchemeCatalogModule`, `EligibilityEngineModule`, `ConversationalRagModule`, `DocumentAuditModule`, `ComplianceAndAuditModule`) enforce strict architectural isolation without the penalties of distributed computing.
- In-memory function execution delivers sub-5ms module-to-module communication.
- Single container deployment keeps cloud hosting expenses minimal.
- If a specific module (e.g., RAG vector search) requires specialized GPU infrastructure in future milestones, its clean interface boundary permits extraction into an independent service with zero internal refactoring.

## Consequences
### Positive:
- Simplified continuous deployment (single Docker image).
- ACID transaction boundaries between scheme versions and AST rules.
- Rapid developer onboarding and local testing without docker-compose meshes.

### Negative / Trade-offs:
- Modules share CPU and memory resources; an unconstrained search query could theoretically impact eligibility evaluation throughput (mitigated via database read-replicas and async worker pools).
- Requires strict code linting and architectural tests (e.g., ArchUnit / import-linter) to prevent developers from violating internal module boundaries.
