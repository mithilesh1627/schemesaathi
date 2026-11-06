"""Document Extractors: Digital PDF (pypdf), Scanned PDF (PaddleOCR), and HTML (BeautifulSoup)."""

import hashlib
import io
import os
import re
from typing import Any

import numpy as np
import pypdf
import pypdfium2 as pdfium
from bs4 import BeautifulSoup

from src.core.errors import StorageError
from src.core.logging import get_logger
from src.modules.retrieval.domain.chunker import redact_pii_text
from src.modules.retrieval.domain.models import DocumentExtractionResult

logger = get_logger(__name__)

# Disable remote model source check during PaddleX / PaddleOCR initialization
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"


class DigitalPdfExtractor:
    """Extracts structured text and metadata from digital PDF documents."""

    @staticmethod
    def extract(pdf_bytes: bytes, source_name: str, source_url: str) -> DocumentExtractionResult:
        """Extract text and detect sections from digital PDF bytes."""
        try:
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        except Exception as exc:
            raise StorageError(f"Failed to parse PDF document {source_name}: {exc}") from exc

        page_count = len(reader.pages)
        full_text_pages: list[str] = []

        for _page_idx, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            # Normalize rupee glyphs commonly extracted as black square from Helvetica fonts
            normalized_text = page_text.replace("\u25a0", "₹")
            redacted_page_text = redact_pii_text(normalized_text)
            full_text_pages.append(redacted_page_text)

        full_text = "\n\n".join(full_text_pages)
        if not full_text.strip():
            # Fallback for non-standard or text-based mock payloads
            decoded = pdf_bytes.decode("utf-8", errors="ignore")
            full_text = redact_pii_text(decoded)
            if full_text.strip() and page_count == 0:
                page_count = 1

        char_count = len(full_text)
        doc_hash = hashlib.sha256(pdf_bytes).hexdigest()

        return DocumentExtractionResult(
            document_name=source_name,
            source_url=source_url,
            content_sha256=doc_hash,
            page_count=page_count,
            character_count=char_count,
            extraction_mode="DIGITAL_TEXT",
            raw_text=full_text,
            tables=[],
        )


class ScannedPdfOcrExtractor:
    """Extracts text from scanned government notifications via OCR (pypdfium2 + PaddleOCR)."""

    def __init__(self, enable_mkldnn: bool = False) -> None:
        self._ocr = None
        self._enable_mkldnn = enable_mkldnn

    def _get_ocr(self) -> Any:
        if self._ocr is None:
            try:
                from paddleocr import PaddleOCR

                # enable_mkldnn=False bypasses oneDNN PIR instruction bug on CPU
                self._ocr = PaddleOCR(
                    ocr_version="PP-OCRv4",
                    use_doc_orientation_classify=False,
                    use_doc_unwarping=False,
                    use_textline_orientation=False,
                    enable_mkldnn=self._enable_mkldnn,
                )
                logger.info("PaddleOCR PP-OCRv4 engine initialized successfully.")
            except Exception as exc:
                logger.error("PaddleOCR initialization failed: %s", exc)
                raise StorageError(f"PaddleOCR failed to initialize: {exc}") from exc
        return self._ocr

    def is_available(self) -> bool:
        try:
            import paddleocr  # noqa: F401
            import pypdfium2  # noqa: F401

            return True
        except ImportError:
            return False

    def extract(
        self, pdf_bytes: bytes, source_name: str, source_url: str
    ) -> DocumentExtractionResult:
        """Run OCR over scanned PDF pages using pypdfium2 rendering and PaddleOCR."""
        try:
            pdf = pdfium.PdfDocument(pdf_bytes)
        except Exception as exc:
            raise StorageError(f"Failed to load PDF document for OCR {source_name}: {exc}") from exc

        page_count = len(pdf)
        extracted_pages: list[str] = []
        ocr_engine = self._get_ocr()

        for page_idx in range(page_count):
            try:
                page = pdf[page_idx]
                pil_img = page.render(scale=2.0).to_pil()
                img_arr = np.array(pil_img.convert("RGB"))

                # In paddleocr 3.x / paddlex, use predict(img_arr)
                result = ocr_engine.predict(img_arr)
                page_lines: list[str] = []

                for res in result:
                    if isinstance(res, dict) and "rec_texts" in res:
                        page_lines.extend(res["rec_texts"])
                    elif hasattr(res, "get") and res.get("rec_texts"):
                        page_lines.extend(res.get("rec_texts"))
                    elif hasattr(res, "rec_texts"):
                        page_lines.extend(res.rec_texts)
                    elif isinstance(res, list):
                        for line in res:
                            if len(line) >= 2 and isinstance(line[1], (tuple, list)):
                                page_lines.append(str(line[1][0]))

                page_raw = "\n".join(page_lines)
                redacted_page_text = redact_pii_text(page_raw)
                extracted_pages.append(redacted_page_text)
            except Exception as page_exc:
                logger.warning(
                    "OCR failed on page %d of %s: %s", page_idx + 1, source_name, page_exc
                )

        full_text = "\n\n".join(extracted_pages)
        char_count = len(full_text)
        doc_hash = hashlib.sha256(pdf_bytes).hexdigest()

        return DocumentExtractionResult(
            document_name=source_name,
            source_url=source_url,
            content_sha256=doc_hash,
            page_count=page_count,
            character_count=char_count,
            extraction_mode="OCR",
            raw_text=full_text,
            tables=[],
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
