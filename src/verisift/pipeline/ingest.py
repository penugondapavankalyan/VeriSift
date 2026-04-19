# VeriSift/src/verisift/pipeline/ingest.py
import fitz  # PyMuPDF
from pdf2image import convert_from_path # Renders PDF pages into images
from dataclasses import dataclass # To create structured data objects
from typing import List # For type-hinting lists of objects
import numpy as np 
import re 
import logging
from ..config import VerisiftConfig # Importing settings

# Set up a logger for this specific module
logger = logging.getLogger(__name__)

@dataclass
class PageData:
    """A container for all data belonging to a single PDF page."""
    index: int
    raw_text: str
    clean_text: str
    image: np.ndarray # The visual 'snapshot' of the page
    is_scanned: bool # Flag for 'Image-PDF' edge case logic

@dataclass
class DocumentData:
    """A container for the entire PDF document and its metadata."""
    path: str
    pages: List[PageData]
    metadata: dict

def ingest_pdf(file_path: str, config: VerisiftConfig) -> DocumentData:
    """
    The 'Entry Point' for reading a PDF. It extracts text, 
    applies exclusions, and renders images based on the config.
    """
    
    # 1. Open the PDF file handle using PyMuPDF (fitz)
    try:
        doc = fitz.open(file_path)
        logger.debug(f"PDF at {file_path} opened successfully.")
    except Exception as e:
        logger.error(f"Failed to open PDF at {file_path}: {e}")
        raise

    
    # 2. Render all pages as images at the DPI specified in our Config
    # It requires 'poppler' to be installed on the system.
    logger.info(f"Rendering pages at {config.dpi} DPI...")
    images = convert_from_path(file_path, dpi=config.dpi, poppler_path=config.poppler_path)
    logger.debug(f"Rendered {len(images)} pages.")
    
    extracted_pages = []
    
    # 3. To pair the PDF page object with its rendered image
    for i, (page, pil_img) in enumerate(zip(doc, images)):
        
        # 4. Extract raw text from the page
        raw_text = page.get_text("text")
        
        # 5. Apply 'Smart Exclusions' (Regex)
        # Why: This removes dynamic data (dates/IDs) so they don't trigger a 'false' difference.
        # clean_text = " ".join(raw_text.split(" "))
        # clean_text = "\n".join(" ".join(line.split()) for line in raw_text.splitlines())
        #  Split and handle hyphenation at end of lines
        raw_text = raw_text.replace("-\n", "").replace("- \n", "")

        clean_lines = []
        for line in raw_text.splitlines():
            stripped_line = " ".join(line.split())
            if stripped_line: # Only add if the line isn't just whitespace
                clean_lines.append(stripped_line)
        clean_text = " ".join(clean_lines)


        if config.ignore_patterns_flag:
            if config.ignore_patterns and len(config.ignore_patterns) > 0:
                logger.debug(f"Applying regex exclusions to page {i+1}")
                for pattern in config.ignore_patterns:
                    # clean_text = re.sub(pattern, "[IGNORED]", clean_text)
                    clean_text = re.sub(pattern, \
                            lambda m: f'VERISIFT_START {m.group(0)} [IGNORED] VERISIFT_END', 
                            clean_text)
            else:
                logger.warning("⚠️ ignore patterns set to 'True' \
                    but no matching patterns for exclusions are provided. \
                    continuiing comparison without exclusions. \
                    set '--ignore_patterns [<regex_patterns>]' to apply exclusions.")
        
        # 6. Check for 'Scanned' status
        # Why: If text length is < 10 characters, it's likely an image (triggers edge case).
        is_scanned_flag = len(raw_text) < 10

        if is_scanned_flag:
            logger.warning(f"Page {i+1} appears to be an image/scanned page (no text found).")
        
        # 7. Package the page into structured PageData class
        # Why: Converting the PIL image to a NumPy array makes it ready for OpenCV/SSIM later.
        extracted_pages.append(PageData(
            index=i,
            raw_text=raw_text,
            clean_text=clean_text,
            image=np.array(pil_img),
            is_scanned=is_scanned_flag
        ))

    logger.info(f"Successfully ingested {len(extracted_pages)} pages from {file_path}")

    # 8. Return the full DocumentData object
    # Why: This keeps the file path and metadata attached to the page data for reporting.
    result = DocumentData(
        path=file_path,
        pages=extracted_pages,
        metadata=doc.metadata
    )
    
    doc.close() # closing the file
    logger.debug(f"PDF at {file_path} closed.")
    return result