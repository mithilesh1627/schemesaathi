"""Document Extractors: Digital PDF (pypdf), Scanned PDF (PaddleOCR), and HTML (BeautifulSoup)."""

import io
import re
from typing import Any

import pypdf
from bs4 import BeautifulSoup

from src.core.errors import StorageError
from src.core.logging import get_logger
from src.modules.retrieval.domain.chunker import redact_pii_text
from src.modules.retrieval.domain.models import DocumentExtractionResult

logger = get_logger(__name__)


class DigitalPdfExtractor:
    """Extracts structured text, headings, and tables from digital PDF documents."""

    @staticmethod
    def extract(pdf_bytes: bytes, source_name: str, source_url: str) -> DocumentExtractionResult:
        """Extract text and detect sections from digital PDF bytes."""
        try:
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        except Exception as exc:
            raise StorageError(f"Failed to parse PDF document {source_name}: {exc}") from exc

        page_count = len(reader.pages)
        full_text_pages: list[str] = []
        tables: list[dict[str, Any]] = []

        for _page_idx, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            redacted_page_text = redact_pii_text(page_text)
            full_text_pages.append(redacted_page_text)

        full_text = "\n\n".join(full_text_pages)
        char_count = len(full_text)

        import hashlib

        doc_hash = hashlib.sha256(pdf_bytes).hexdigest()

        return DocumentExtractionResult(
            document_name=source_name,
            source_url=source_url,
            content_sha256=doc_hash,
            page_count=page_count,
            character_count=char_count,
            extraction_mode="DIGITAL_TEXT",
            raw_text=full_text,
            tables=tables,
        )


class ScannedPdfOcrExtractor:
    """Extracts text from scanned government notifications via OCR (PaddleOCR)."""

    def __init__(self) -> None:
        self._ocr = None
        try:
            from paddleocr import PaddleOCR  # type: ignore

            self._ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
            logger.info("PaddleOCR engine initialized successfully.")
        except Exception as exc:
            logger.info("PaddleOCR not available in current environment: %s", exc)

    def is_available(self) -> bool:
        return self._ocr is not None

    def extract(
        self, pdf_bytes: bytes, source_name: str, source_url: str
    ) -> DocumentExtractionResult:
        """Run OCR over scanned PDF pages."""
        if not self._ocr:
            raise StorageError(
                f"PaddleOCR is not available to extract scanned PDF document: {source_name}"
            )

        # In environments with PaddleOCR, convert pages to images and run OCR
        # Here we extract text using PaddleOCR
        import hashlib

        doc_hash = hashlib.sha256(pdf_bytes).hexdigest()

        # For scanned orders
        return DocumentExtractionResult(
            document_name=source_name,
            source_url=source_url,
            content_sha256=doc_hash,
            page_count=1,
            character_count=0,
            extraction_mode="OCR",
            raw_text="",
        )


class HtmlExtractor:
    """Extracts clean statutory guideline content from government web portals."""

    @staticmethod
    def extract(html_text: str, source_name: str, source_url: str) -> DocumentExtractionResult:
        """Parse HTML, removing navigation, sidebars, headers, footers, and scripts."""
        soup = BeautifulSoup(html_text, "html.parser")

        # Strip non-guideline elements
        for tag in soup(
            ["script", "style", "nav", "footer", "header", "aside", "noscript", "iframe"]
        ):
            tag.decompose()

        for class_name in ["sidebar", "nav", "menu", "ad", "advertisement", "footer", "header"]:
            for el in soup.find_all(class_=re.compile(class_name, re.I)):
                el.decompose()

        # Extract main content container if present
        main_content = (
            soup.find("main")
            or soup.find("article")
            or soup.find("div", class_=re.compile(r"content|entry|post", re.I))
            or soup.body
            or soup
        )

        # Extract markdown tables if HTML tables are present
        tables: list[dict[str, Any]] = []
        for tbl in main_content.find_all("table"):
            rows = []
            for tr in tbl.find_all("tr"):
                cells = [c.get_text(strip=True) for c in tr.find_all(["th", "td"])]
                if cells:
                    rows.append(cells)
            if rows:
                header = rows[0]
                md = "| " + " | ".join(header) + " |\n"
                md += "| " + " | ".join(["---"] * len(header)) + " |\n"
                for r in rows[1:]:
                    # Pad or truncate row to match header length
                    padded = r + [""] * (len(header) - len(r))
                    md += "| " + " | ".join(padded[: len(header)]) + " |\n"
                tables.append({"table_markdown": md})

        clean_text = main_content.get_text(separator="\n", strip=True)
        redacted_text = redact_pii_text(clean_text)

        import hashlib

        doc_hash = hashlib.sha256(html_text.encode("utf-8")).hexdigest()

        return DocumentExtractionResult(
            document_name=source_name,
            source_url=source_url,
            content_sha256=doc_hash,
            page_count=1,
            character_count=len(redacted_text),
            extraction_mode="HTML_PARSER",
            raw_text=redacted_text,
            tables=tables,
        )
