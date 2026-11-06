"""Hierarchical, Table-Preserving Text and Table Chunker."""

import hashlib
import re
import uuid
from typing import Any

from src.modules.retrieval.domain.models import KnowledgeChunk

# Approximate tokenization using whitespace and punctuation boundaries
TOKEN_PATTERN = re.compile(r"\w+|[^\w\s]")
# Unconditional 12-digit sequence matcher (not relying on whitespace boundaries for OCR robustness)
AADHAAR_PATTERN = re.compile(r"(?<!\d)\d{12}(?!\d)")


def redact_pii_text(text: str) -> str:
    """Unconditionally redact any 12-digit sequence (Aadhaar guardrail)."""
    return AADHAAR_PATTERN.sub("[REDACTED_AADHAAR]", text)


def count_tokens(text: str) -> int:
    """Count tokens using robust regex tokenizer."""
    return len(TOKEN_PATTERN.findall(text))


def split_into_sentences(text: str) -> list[str]:
    """Split text along domain-aware sentence boundaries."""
    # Split on double newline or period/semicolon/question mark followed by space or newline
    raw_sentences = re.split(r"(?<=[.!?;\n])\s+(?=[A-Z0-9\[\(\-\•])", text)
    sentences: list[str] = []
    for s in raw_sentences:
        s_clean = s.strip()
        if s_clean:
            sentences.append(s_clean)
    return sentences


class HierarchicalChunker:
    """Splits documents into 512-token chunks with 64-token overlap and zero table fracturing."""

    def __init__(self, max_tokens: int = 512, overlap_tokens: int = 64) -> None:
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens

    def chunk_document_sections(
        self,
        scheme_id: str,
        version_id: uuid.UUID,
        scheme_title: str,
        academic_year: str,
        sections: list[dict[str, Any]],
        language_code: str = "en",
    ) -> list[KnowledgeChunk]:
        """Process sections and tables into enriched KnowledgeChunks."""
        chunks: list[KnowledgeChunk] = []
        chunk_idx = 0

        for sec in sections:
            section_title = sec.get("section_title", "General Guidelines")
            page_number = sec.get("page_number")
            is_table = sec.get("is_table", False)
            content = redact_pii_text(sec.get("content", "").strip())
            table_markdown = sec.get("table_markdown")

            lineage_prefix = f"[Scheme: {scheme_title} | Section: {section_title} | Academic Year: {academic_year}]"

            # Table preservation: never fracture tables
            if is_table or table_markdown:
                table_text = redact_pii_text(table_markdown or content)
                chunk_body = f"{lineage_prefix}\n\n{table_text}"
                tok_cnt = count_tokens(chunk_body)
                c_hash = hashlib.sha256(chunk_body.encode("utf-8")).hexdigest()

                chunks.append(
                    KnowledgeChunk(
                        chunk_id=uuid.uuid4(),
                        scheme_id=scheme_id,
                        version_id=version_id,
                        language_code=language_code,
                        section_title=section_title,
                        lineage_prefix=lineage_prefix,
                        chunk_content=chunk_body,
                        token_count=tok_cnt,
                        content_sha256=c_hash,
                        page_number=page_number,
                        chunk_index=chunk_idx,
                        is_table=True,
                        table_markdown=table_text,
                    )
                )
                chunk_idx += 1
                continue

            # Standard prose: split into domain-aware sentence units
            sentences = split_into_sentences(content)
            if not sentences:
                continue

            current_sentences: list[str] = []

            for sent in sentences:
                test_sentences = current_sentences + [sent]
                test_body = f"{lineage_prefix}\n\n" + " ".join(test_sentences)
                test_token_count = count_tokens(test_body)

                if test_token_count <= self.max_tokens or not current_sentences:
                    current_sentences.append(sent)
                else:
                    # Flush current chunk
                    chunk_text = " ".join(current_sentences)
                    full_chunk_body = f"{lineage_prefix}\n\n{chunk_text}"
                    c_hash = hashlib.sha256(full_chunk_body.encode("utf-8")).hexdigest()

                    chunks.append(
                        KnowledgeChunk(
                            chunk_id=uuid.uuid4(),
                            scheme_id=scheme_id,
                            version_id=version_id,
                            language_code=language_code,
                            section_title=section_title,
                            lineage_prefix=lineage_prefix,
                            chunk_content=full_chunk_body,
                            token_count=count_tokens(full_chunk_body),
                            content_sha256=c_hash,
                            page_number=page_number,
                            chunk_index=chunk_idx,
                            is_table=False,
                        )
                    )
                    chunk_idx += 1

                    # Apply sliding-window overlap of up to overlap_tokens from the end
                    overlap_sents: list[str] = []
                    acc_overlap = 0
                    for prev_sent in reversed(current_sentences):
                        sent_tokens = count_tokens(prev_sent)
                        if acc_overlap + sent_tokens <= self.overlap_tokens:
                            overlap_sents.insert(0, prev_sent)
                            acc_overlap += sent_tokens
                        else:
                            break

                    current_sentences = overlap_sents + [sent]

            # Flush trailing sentences
            if current_sentences:
                chunk_text = " ".join(current_sentences)
                full_chunk_body = f"{lineage_prefix}\n\n{chunk_text}"
                c_hash = hashlib.sha256(full_chunk_body.encode("utf-8")).hexdigest()

                chunks.append(
                    KnowledgeChunk(
                        chunk_id=uuid.uuid4(),
                        scheme_id=scheme_id,
                        version_id=version_id,
                        language_code=language_code,
                        section_title=section_title,
                        lineage_prefix=lineage_prefix,
                        chunk_content=full_chunk_body,
                        token_count=count_tokens(full_chunk_body),
                        content_sha256=c_hash,
                        page_number=page_number,
                        chunk_index=chunk_idx,
                        is_table=False,
                    )
                )
                chunk_idx += 1

        return chunks
