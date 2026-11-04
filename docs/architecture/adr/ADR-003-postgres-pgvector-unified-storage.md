# ADR-003: Unified Storage with PostgreSQL 16 & pgvector

**Status:** Accepted  
**Date:** November 2026  
**Deciders:** Principal AI Engineer, Senior RAG Architect  
**Context:** Database & Vector Store Selection for SchemeSaathi  

---

## Context and Problem Statement
SchemeSaathi requires storing and querying three distinct data modalities:
1. **Relational Data:** Scheme metadata, versions, application windows, AISHE directory, audit events.
2. **Semi-Structured Data:** JSON-Logic Abstract Syntax Trees (ASTs) for dynamic eligibility rules.
3. **Dense Vector Embeddings:** 1536-dimensional embeddings for multilingual semantic search and RAG retrieval across government guidelines.

We must decide between running a dedicated vector database (e.g., Pinecone, Milvus, Qdrant) alongside a relational database, or adopting PostgreSQL 16 with the `pgvector` extension as a unified storage layer.

## Decision Drivers
1. **Transactional Consistency:** When a scheme is updated, its relational rules, JSON-Logic AST, and vector embeddings must be updated atomically within a single ACID transaction.
2. **Operational Simplicity:** Avoid managing two distinct distributed databases, multi-master replication, and network bridges.
3. **Hybrid Search Efficiency:** Ability to execute dense vector search and sparse full-text search (`tsvector`) within a single SQL query using Reciprocal Rank Fusion (RRF).
4. **Cost:** Open-source, zero SaaS licensing fees, self-hostable.

## Considered Options
1. **Option 1: PostgreSQL (Relational/JSONB) + External Managed Vector DB (Pinecone / Qdrant)**
2. **Option 2: Unified PostgreSQL 16 with `pgvector` & HNSW Indexing**

## Decision Outcome
**Chosen Option:** **Option 2: Unified PostgreSQL 16 with `pgvector` & HNSW Indexing**

### Rationale:
- PostgreSQL 16 with `pgvector` (0.5.0+) supports Hierarchical Navigable Small World (HNSW) indexing, delivering sub-20ms approximate nearest neighbor query latency on vector collections exceeding 100,000 items.
- Permits hybrid filtering in a single SQL statement: filtering by statutory criteria (caste, income ceiling) using B-Tree/GIN indexes while simultaneously performing vector cosine distance ranking on the filtered subset.
- Guaranteed ACID consistency: Deleting or rolling back a scheme version instantly removes its associated vector chunks.

## Consequences
### Positive:
- Single backup, replication, and disaster recovery pipeline (standard `pg_dump` and streaming replication).
- Zero third-party cloud data egress costs.
- Native join capabilities between `user_evaluations`, `chat_sessions`, and `scheme_knowledge_chunks`.

### Negative / Trade-offs:
- Heavy batch embedding re-indexing can consume database CPU/memory (mitigated by building HNSW indexes on background worker threads during off-peak hours).
- Vector dimensionality is bound by PostgreSQL limits (maximum 2000 dimensions for HNSW, easily accommodating 1536-dim standard models).
