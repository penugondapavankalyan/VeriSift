# VeriSift/src/verisift/pipeline/report.py
import os
import base64
import cv2
import logging
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from ..models import ComparisonReport
from PyPDF2 import PdfReader

logger = logging.getLogger(__name__)

def _image_to_base64(image_array):
    if image_array is None: return ""
    # Ensure it's a numpy array for CV2
    try:
        _, buffer = cv2.imencode('.png', image_array)
        return base64.b64encode(buffer).decode('utf-8')
    except Exception:
        return ""

def generate_html_report(report: ComparisonReport, output_path: str):
    # Adjust path to find your templates folder
    template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
    env = Environment(loader=FileSystemLoader(template_dir))
    
    try:
        template = env.get_template("report_template.html")
    except Exception as e:
        logger.error(f"Template not found: {e}")
        return False

    # 1. Prepare Page Data (Mapping to template names)
    # The template expects: page.expected_image_base64, page.text_score, etc.
    for p in report.pages:
        p.expected_image_base64 = _image_to_base64(p.expected_image)
        p.actual_image_base64 = _image_to_base64(p.actual_image)
        p.heatmap_base64 = _image_to_base64(p.heatmap)
        # Ensure scores are floats (0.0 to 1.0) as the template rounds them
        p.text_score = float(p.text_score)
        p.visual_score = float(p.visual_score)


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
            return info
        except Exception as e:
            logger.warning(f"Could not read metadata for {pdf_path}: {e}")
            return {}
    
    actual_meta = _get_pdf_properties(report.actual_path)
    logger.debug(f"Actual metadata: {actual_meta}")
    expected_meta = _get_pdf_properties(report.expected_path)
    logger.debug(f"Expected metadata: {expected_meta}")

    metadata_comparison = {
        "actual": {
            "filename": os.path.basename(report.actual_path),
            "filesize": f"{os.path.getsize(report.actual_path) / 1024:.1f} KB" if os.path.exists(report.actual_path) else "N/A",
            "pages": actual_meta.get('page_count', "N/A"),
            "creator": actual_meta.get('/Creator', "N/A")
        },
        "expected": {
            "filename": os.path.basename(report.expected_path),
            "filesize": f"{os.path.getsize(report.expected_path) / 1024:.1f} KB" if os.path.exists(report.expected_path) else "N/A",
            "pages": expected_meta.get('page_count', "N/A"),
            "creator": expected_meta.get('/Creator', "N/A")
        }
    }

    # 3. Final Score Calculations
    if report.pages:
        avg_text = sum(p.text_score for p in report.pages) / len(report.pages)
        avg_visual = sum(p.visual_score for p in report.pages) / len(report.pages)
        intent_score = sum(p.intent_score for p in report.pages) / len(report.pages) if report.pages[0].intent_score is not None else 0.0
        report.overall_score = round(((avg_text + avg_visual) / 2) * 100, 2)
    else:
        report.overall_score = 0.0

    # 4. Render with the names the HTML expects
    try:
        html_content = template.render(
            report=report,  # Pass the whole object so template can access report.pages
            metadata_comparison=metadata_comparison,
            text_score_avg=round(avg_text * 100, 2),   
            visual_score_avg=round(avg_visual * 100, 2), 
            intent_score_avg=round(intent_score * 100, 2),
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