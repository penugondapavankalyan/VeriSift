# VeriSift/src/verisift/pipeline/report.py
import os
import base64
import cv2
import logging
from datetime import datetime
from jinja2 import Environment, FileSystemLoader, TemplateNotFound, TemplateSyntaxError
from ..models import ComparisonReport
from ..config import VerisiftConfig
from PyPDF2 import PdfReader
import re

logger = logging.getLogger(__name__)

def _image_to_base64(image_array):
    if image_array is None: return ""
    # Ensure it's a numpy array for CV2
    try:
        _, buffer = cv2.imencode('.png', image_array)
        return base64.b64encode(buffer).decode('utf-8')
    except Exception:
        return ""

def _parse_pdf_date(date_str):
    if not date_str or not isinstance(date_str, str) or not date_str.startswith('D:'):
        return date_str
    # Extract YYYYMMDDHHMMSS
    match = re.search(r'D:(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})', date_str)
    if match:
        y, m, d, hh, mm, ss = match.groups()
        return f"{y}-{m}-{d} {hh}:{mm}:{ss}"
    return date_str


def _get_pdf_properties(pdf_path: str) -> dict:
    if not pdf_path or not os.path.exists(pdf_path):
        return {} # Return empty dict instead of None to simplify lookups
    try:
        # Use PdfReader metadata but convert to a standard dict for safety
        reader = PdfReader(pdf_path)
        meta = reader.metadata
        info = dict(meta) if meta else {}
        # Extract page count from the reader itself, as it's not in metadata
        info['page_count'] = len(reader.pages)
        info['is_encrypted'] = "Yes" if reader.is_encrypted else "No"
        return info
    except Exception as e:
        logger.warning(f"Could not read metadata for {pdf_path}: {e}")
        return {}

def build_meta_dict(path, meta):
    return {
            "filename": os.path.basename(path),
            "filesize": f"{os.path.getsize(path) / 1024:.1f} KB" if os.path.exists(path) else "N/A",
            "filepath": path,
            "pages": meta.get('page_count', "N/A"),
            "createdate": _parse_pdf_date(meta.get('/CreationDate', "N/A")),
            "modifieddate": _parse_pdf_date(meta.get('/ModDate', "N/A")),
            "creator": meta.get('/Creator', "N/A"),
            "author": meta.get('/Author', "N/A"),
            "encryption": meta.get('is_encrypted', "No")
        }


def generate_html_report(report: ComparisonReport, output_path: str = None) -> bool:
    if output_path is None:
        config = VerisiftConfig()
        output_path = os.path.join(config.output_dir, config.report_name)

    # Adjust path to find your templates folder
    template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "templates"))
    env = Environment(loader=FileSystemLoader(template_dir), autoescape=True)

    try:
        template = env.get_template("report_template.html")
    except TemplateNotFound:
        logger.error(f"Template 'report_template.html' not found in: {template_dir}")
        return False
    except TemplateSyntaxError as e:
        logger.error(f"Syntax error in template '{e.name}' at line {e.lineno}: {e.message}")
        return False
    except Exception as e:
        logger.error(f"Template not found: {e}")
        logger.error(f"Unexpected error loading template: {e}")
        return False

    # 1. Prepare Page Data (Mapping to template names)
    # The template expects: page.expected_image_base64, page.text_score, etc.
    for p in report.pages:
        p.expected_image_base64 = _image_to_base64(p.expected_image)
        p.actual_image_base64 = _image_to_base64(p.actual_image)
        p.heatmap_base64 = _image_to_base64(p.heatmap)
        # Ensure scores are floats (0.0 to 1.0) as the template rounds them
        p.text_score = float(p.text_score)
        p.visual_score = float(p.visual_score) if p.visual_score is not None else None
   
    actual_meta = _get_pdf_properties(report.actual_path)
    logger.debug(f"Actual metadata: {actual_meta}")
    expected_meta = _get_pdf_properties(report.expected_path)
    logger.debug(f"Expected metadata: {expected_meta}")

    metadata_comparison = {
            "actual": build_meta_dict(report.actual_path, actual_meta),
            "expected": build_meta_dict(report.expected_path, expected_meta)
        }


    # 3. Final Score Preparations for Template
    # We avoid re-calculating global scores here to maintain consistency with core.py logic.
    # avg_text = sum(p.text_score for p in report.pages) / len(report.pages) if report.pages else 0.0
    avg_text = report.text_score_avg if report.text_score_avg is not None else 0.0
    # avg_visual = sum(p.visual_score for p in report.pages if p.visual_score is not None) / len(report.pages) if VerisiftConfig.enable_visual else None
    avg_visual = report.visual_score_avg if report.visual_score_avg is not None else 0.0
    intent_score_val = report.avg_intent_score if report.avg_intent_score is not None else 0.0

    # 4. Render with the names the HTML expects
    try:
        html_content = template.render(
            report=report,  # Pass the whole object so template can access report.pages
            metadata_comparison=metadata_comparison,
            text_score_avg=round(avg_text * 100, 2),   
            visual_score_avg=round(avg_visual * 100, 2), 
            intent_score_avg=round(intent_score_val, 2),
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            run_id=f"cmp_{os.urandom(3).hex()}"
        )

        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        logger.info(f"Successfully generated report at: {output_path}")
        return True

    except Exception as e:
        logger.error(f"Error during template rendering: {e}")
        return False