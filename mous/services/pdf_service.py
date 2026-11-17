import re
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import pdfplumber
from pypdf import PdfReader

logger = logging.getLogger(__name__)

DATE_PATTERNS = [
    r'\b(\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})\b',
    r'\b((?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},?\s+\d{4})\b',
    r'\b(\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4})\b',
]


class PDFProcessingService:
    """Service for extracting text, metadata, and detected dates from PDF agreements."""

    @staticmethod
    def extract_document_data(file_path_or_buffer) -> Dict[str, Any]:
        """
        Extracts full text, page count, and candidate dates from an uploaded PDF.
        Returns a dict with 'text', 'page_count', 'dates_found', and 'metadata'.
        """
        extracted_pages: List[str] = []
        page_count = 0
        dates_found: List[str] = []

        try:
            with pdfplumber.open(file_path_or_buffer) as pdf:
                page_count = len(pdf.pages)
                for index, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text() or ''
                    if text.strip():
                        extracted_pages.append(text.strip())
        except Exception as e:
            logger.warning(f"pdfplumber extraction failed, attempting fallback to pypdf: {e}")
            try:
                reader = PdfReader(file_path_or_buffer)
                page_count = len(reader.pages)
                for page in reader.pages:
                    text = page.extract_text() or ''
                    if text.strip():
                        extracted_pages.append(text.strip())
            except Exception as fallback_err:
                logger.error(f"Both pdfplumber and pypdf extraction failed: {fallback_err}")
                return {
                    'text': '',
                    'page_count': 0,
                    'dates_found': [],
                    'error': str(fallback_err),
                }

        full_text = "\n\n--- Page Break ---\n\n".join(extracted_pages)

        # Extract potential dates
        for pattern in DATE_PATTERNS:
            matches = re.findall(pattern, full_text, flags=re.IGNORECASE)
            for m in matches:
                if m not in dates_found:
                    dates_found.append(m)

        return {
            'text': full_text,
            'page_count': page_count,
            'dates_found': dates_found[:10],
            'pages': extracted_pages,
        }
