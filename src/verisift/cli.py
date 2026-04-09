# VeriSift/src/verisift/cli.py
import argparse
import sys
import os
import subprocess
import logging
from typing import Optional

# Internal Imports
from .config import VerisiftConfig
from .core import Comparator
from .utils.health import run_health_check
from .utils.config_manager import ConfigManager
from .pipeline.report import generate_html_report

# Initialize Logger
logger = logging.getLogger(__name__)

def main():
    # Initialize the Configuration Manager for ~/.verisift/config.json
    cfg_mgr = ConfigManager()
    
    parser = argparse.ArgumentParser(
        prog="verisift",
        description="Verisift: Professional PDF Comparison Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  verisift run actual.pdf expected.pdf
  verisift run a.pdf e.pdf --mode semantic --outdir ./audits
  verisift set-config --mode semantic --dpi 300
  verisift ui
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Available Commands")

    # --- COMMAND: run ---
    run_parser = subparsers.add_parser("run", help="Compare two PDF documents")
    run_parser.add_argument("actual", help="Path to the actual PDF file")
    run_parser.add_argument("expected", help="Path to the expected PDF file")
    run_parser.add_argument("--outdir", "-o", help="Directory to save the report")
    run_parser.add_argument("--reportname", "-rn", help="Custom name for the HTML report")
    run_parser.add_argument("--mode", choices=["literal", "semantic"], help="Override comparison mode")
    run_parser.add_argument("--dpi", type=int, help="Override rendering DPI")

    # --- COMMAND: health-check ---
    subparsers.add_parser("health-check", help="Verify system dependencies (Poppler/Tesseract)")

    # --- COMMAND: display-config ---
    subparsers.add_parser("display-config", help="Show current global configurations")

    # --- COMMAND: set-config ---
    set_parser = subparsers.add_parser("set-config", help="Permanently update default settings")
    set_parser.add_argument("--mode", choices=["literal", "semantic"], help="Set default comparison mode")
    set_parser.add_argument("--dpi", type=int, help="Set default rendering DPI")
    set_parser.add_argument("--outdir", help="Set default output directory")

    # --- COMMAND: reset-config ---
    subparsers.add_parser("reset-config", help="Restore all settings to factory defaults")

    # --- COMMAND: ui ---
    subparsers.add_parser("ui", help="Launch the Streamlit Web Interface")

    args = parser.parse_args()

    # --- ROUTING LOGIC ---

    # 1. DEFAULT DASHBOARD (Just typing 'verisift')
    if args.command is None:
        print("\n--- Verisift Engine v1.0 ---")
        is_ok, _ = run_health_check()
        status = "READY" if is_ok else "INCOMPLETE (run 'verisift health-check')"
        print(f"System Health: {status}")
        print("\nQuick Start: verisift run 'actual.pdf' 'expected.pdf'")
        parser.print_help()
        sys.exit(0)

    # 2. HEALTH CHECK
    if args.command == "health-check":
        print("[*] Running System Dependency Check...")
        is_ok, missing = run_health_check()
        if is_ok:
            print("[SUCCESS] All system dependencies (Poppler/Tesseract) are installed.")
        else:
            print("[ERROR] Missing the following system tools:")
            for item in missing:
                print(f"  - {item}")
            print("\nPlease install these via your OS package manager.")
        sys.exit(0 if is_ok else 1)

    # 3. RUN COMPARISON
    elif args.command == "run":
        # Check health silently before starting
        is_ok, missing = run_health_check()
        if not is_ok:
            print(f"[ERROR] Cannot run. Missing dependencies: {', '.join(missing)}")
            sys.exit(1)

        # LOAD CONFIG: Layered priority (Default < User File < CLI Flags)
        # Using type hint for better IDE support and code clarity
        config: VerisiftConfig = cfg_mgr.load_user_config()
        
        # Apply CLI overrides if provided
        if args.mode: config.comparison_mode = args.mode
        if args.dpi: config.dpi = args.dpi
        if args.outdir: config.output_dir = args.outdir
        if args.reportname: config.report_name = args.reportname

        print(f"[*] Comparing: {os.path.basename(args.actual)} vs {os.path.basename(args.expected)}")
        print(f"[*] Config: Mode={config.comparison_mode.upper()}, DPI={config.dpi}")

        try:
            comparator = Comparator(config)
            report = comparator.compare(args.actual, args.expected)
            
            os.makedirs(config.output_dir, exist_ok=True)
            report_path = os.path.join(config.output_dir, config.report_name)
            
            if generate_html_report(report, report_path):
                print(f"\n[SUCCESS] Report generated: {os.path.abspath(report_path)}")
        except Exception as e:
            print(f"[CRITICAL ERROR] {str(e)}")
            sys.exit(1)

    # 4. CONFIG MANAGEMENT
    elif args.command == "display-config":
        current_cfg = cfg_mgr.load_user_config()
        print("\n--- Verisift Current Settings ---")
        for key, value in current_cfg.__dict__.items():
            print(f"{key:20}: {value}")
        print("")

    elif args.command == "set-config":
        if not any([args.mode, args.dpi, args.outdir]):
            print("[INFO] No changes specified. Use --mode, --dpi, or --outdir.")
        else:
            if args.mode: cfg_mgr.set_config("comparison_mode", args.mode)
            if args.dpi: cfg_mgr.set_config("dpi", args.dpi)
            if args.outdir: cfg_mgr.set_config("output_dir", args.outdir)
            print("[SUCCESS] Global settings updated permanently.")

    elif args.command == "reset-config":
        if cfg_mgr.reset_to_defaults():
            print("[SUCCESS] All settings restored to factory defaults.")
        else:
            print("[INFO] Settings were already at default values.")

    # 5. STREAMLIT UI
    elif args.command == "ui":
        ui_path = os.path.join(os.path.dirname(__file__), "ui", "app.py")
        if not os.path.exists(ui_path):
            print("[ERROR] UI module not found.")
            sys.exit(1)
        
        print("[*] Launching Streamlit UI...")
        subprocess.run(["streamlit", "run", ui_path])

if __name__ == "__main__":
    main()