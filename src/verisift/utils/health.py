# # VeriSift/src/verisift/utils/health.py

import shutil
import logging
import subprocess
import sys

logger = logging.getLogger(__name__)

def check_system_dependencies(ocr_enabled: bool = False):
    """
    Checks for non-python dependencies that PyPI cannot install.
    """
    dependencies = {
        "pdftoppm": "Poppler (required for PDF rendering)",
        "pdftocairo": "Poppler (required for PDF rendering)"
    }
    
    if ocr_enabled:
        dependencies["tesseract"] = "Tesseract OCR (required for scanned PDFs)"

    missing = []
    for cmd, desc in dependencies.items():
        if shutil.which(cmd) is None:
            missing.append(f"- {cmd} ({desc})")

    if missing:
        logger.error("Missing System Dependencies:\n" + "\n".join(missing))
        return False, missing
    
    return True, []

def run_health_check(exit_on_failure: bool = False):
    """
    Main entry point for health checks used by CLI and UI.
    """
    logger.info("Running Verisift Health Check...")
    success, missing = check_system_dependencies()
    
    if not success:
        print("\n[!] VERISIFT SYSTEM CHECK FAILED")
        for m in missing:
            print(m)
        print("\nConsult the README for installation instructions (brew/apt-get install).")
        
        if exit_on_failure:
            sys.exit(1)
            
    return success, missing
