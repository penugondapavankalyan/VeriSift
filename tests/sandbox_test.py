# # VeriSift/test/sandbox_test.py
import logging
import sys
from pathlib import Path
import os

# Add parent directory to path to import src module
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.verisift.config import VerisiftConfig
from src.verisift.core import Comparator
from src.verisift.utils.health import run_health_check
from src.verisift.pipeline.report import generate_html_report


# Setup logging to see what's happening under the hood
logging.basicConfig(level=logging.INFO)

def run_local_audit(pdf_a, pdf_b, semantic_compare=False, utput_dir=VerisiftConfig.output_dir, report_name=VerisiftConfig.report_name):
    # 1. Manual Health Check
    is_ok, missing = run_health_check()
    if not is_ok:
        print(f"Fix your system first! Missing: {missing}")
        return

    # 2. Define Configuration
    # We use a lower DPI for the first test to save RAM
    if semantic_compare:
        config = VerisiftConfig(
            comparison_mode="semantic", 
            dpi=150,
            poppler_path = r"C:\Program Files\poppler\poppler-25.12.0\Library\bin"
        )
    else:
        config = VerisiftConfig(
        comparison_mode="literal", 
        dpi=150,
        poppler_path = r"C:\Program Files\poppler\poppler-25.12.0\Library\bin"
        )

    # 3. Trigger the Engine
    print(f"[*] Initializing Verisift for {pdf_a}...")
    engine = Comparator(config)
    
    try:
        report = engine.compare(pdf_a, pdf_b)
        print(f"[SUCCESS] Comparison finished. Total pages: {report.total_pages}")
        print(f"[*] Match Score: {report.overall_score}%")
        # print(f"report info: {report}")

        try:      
            os.makedirs(config.output_dir, exist_ok=True)

            # COMBINE THE PATH HERE
            full_report_path = os.path.join(output_dir, report_name)
            # print(f"full report path: {full_report_path}")

            # Pass the full_report_path instead of just the directory
            generate_html_report(report, full_report_path)
            
            # print(f"[SUCCESS] Report saved to: {full_report_path}")
            
        except Exception as e:
            print(f"[FAIL] Report generation failed: {e}")

    except Exception as e:
        print(f"[FAIL] Engine crashed: {e}")

if __name__ == "__main__":
    # Replace these with your actual test files
    ACTUAL = r"C:\Users\PenugondaPavanKalyan\Downloads\verisift\Electronic_Warfare_actual.pdf"
    EXPECTED = r"C:\Users\PenugondaPavanKalyan\Downloads\verisift\Electronic_Warfare.pdf"
    ACTUAL1 = r"C:\Users\PenugondaPavanKalyan\Downloads\verisift\Electronic_Warfare1.pdf"
    ACTUAL2 = r"C:\Users\PenugondaPavanKalyan\Downloads\verisift\Electronic_Warfare2.pdf"
    ACTUAL3 = r"C:\Users\PenugondaPavanKalyan\Downloads\verisift\Modern_Warfare_Technology_actual.pdf"
    EXPECTED3 = r"C:\Users\PenugondaPavanKalyan\Downloads\verisift\Modern_Warfare_Technology.pdf"
    semantic_actual = r"C:\Users\PenugondaPavanKalyan\Downloads\verisift\Electronic_Warfare_semantic.pdf"
    actual_semantic = r"C:\Users\PenugondaPavanKalyan\Downloads\verisift\Electronic_Warfare_semantic_actual.pdf"
    expected_semantic = r"C:\Users\PenugondaPavanKalyan\Downloads\verisift\Electronic_Warfare_semantic_expected.pdf"

    output_dir = r"C:\Users\PenugondaPavanKalyan\Downloads\verisift"
    report_name = "test_report.html"
    semantic_compare = True
    # semantic_compare = False
    # run_local_audit(ACTUAL1, EXPECTED, semantic_compare, output_dir, report_name)
    # run_local_audit(semantic_actual, EXPECTED, semantic_compare, output_dir, report_name)
    # run_local_audit(EXPECTED, EXPECTED, semantic_compare, output_dir, report_name)
    # run_local_audit(ACTUAL3, EXPECTED3, semantic_compare, output_dir, report_name)
    run_local_audit(actual_semantic, expected_semantic, semantic_compare, output_dir, report_name)