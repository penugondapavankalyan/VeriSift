# # VeriSift/src/verisift/cli.py
# import argparse
# import sys
# import os
# import subprocess
# import logging
# from typing import Optional

# # Internal Imports
# from .config import VerisiftConfig
# from .core import Comparator
# from .utils.health import run_health_check
# from .utils.config_manager import ConfigManager
# from .pipeline.report import generate_html_report

# # Initialize Logger
# logger = logging.getLogger(__name__)


# def handle_set_config(args):
#     # Load existing config to update it
#     config = VerisiftConfig.load_from_disk()
    
#     # Mapping CLI args to Config attributes
#     mapping = {
#         "mode": "comparison_mode",
#         "dpi": "dpi",
#         "outputdir": "output_dir",
#         "reportname": "report_name",
#         "semantic_threshold": "semantic_threshold",
#         "semantic_max_phrase": "semantic_max_phrase",
#         "enable_visual": "enable_visual",
#         "ignore_patterns_flag": "ignore_patterns_flag",
#         "popplerpath": "poppler_path",
#         "txt_weightage": "txt_weightage",
#         "text_threshold": "text_threshold",
#         "visual_threshold": "visual_threshold"
#     }

#     changes = False
#     for arg_name, config_attr in mapping.items():
#         val = getattr(args, arg_name, None)
#         if val is not None:
#             # Range validation for floats
#             if config_attr in ["txt_weightage", "text_threshold", "visual_threshold", "semantic_threshold"]:
#                 if not (0 <= val <= 1):
#                     print(f"Error: {arg_name} must be between 0.0 and 1.0")
#                     return
            
#             setattr(config, config_attr, val)
#             logger.info(f"✅ Set {config_attr} -> {val}")
#             changes = True

#     if changes:
#         try:
#             config.save_to_disk()
#             logger.info("Config saved successfully. To reset configurations to default use 'verisift reset-config'.")
#             return True
#         except Exception as e:  
#             logger.error(f"❌ Error saving config: {e}")
#             return False
#     else:
#         logger.info("No changes provided. Use 'verisift set-config --help' to see options.")


# def main():
#     # Initialize the Configuration Manager for ~/.verisift/config.json
#     cfg_mgr = ConfigManager()
    
#     parser = argparse.ArgumentParser(
#         prog="verisift",
#         description="Verisift: Professional PDF Comparison Engine",
#         formatter_class=argparse.RawDescriptionHelpFormatter,
#         epilog="""
#         Examples:
#         verisift run actual.pdf expected.pdf
#         verisift run a.pdf e.pdf --mode semantic --outdir ./audits
#         verisift set-config --mode semantic --dpi 300
#         verisift ui
#         """
#     )

#     subparsers = parser.add_subparsers(dest="command", help="Available Commands")

#     # --- COMMAND: run ---
#     run_parser = subparsers.add_parser("run", help="Compare two PDF documents")
#     run_parser.add_argument("--actual", help="Path to the actual PDF file")
#     run_parser.add_argument("--expected", help="Path to the expected PDF file")
#     run_parser.add_argument("--outputdir", "-o", help="Filepath to save report")
#     run_parser.add_argument("--reportname", "-rn", help="Custom name for the HTML report")
#     run_parser.add_argument("--mode", choices=["literal", "semantic"], help="Choose comparison mode")
#     run_parser.add_argument("--dpi", type=int, help="Override rendering DPI")

#     # --- COMMAND: health-check ---
#     subparsers.add_parser("health-check", help="Verify system dependencies (Poppler)")

#     # --- COMMAND: display-config ---
#     subparsers.add_parser("display-config", help="Show current configurations")

#     # --- COMMAND: set-config ---
#     set_parser = subparsers.add_parser("set-config", help="Permanently update default settings")
#     set_parser.add_argument("--mode", choices=["literal", "semantic"], help="Set default comparison mode")
#     set_parser.add_argument("--dpi", type=int, help="Set default rendering DPI")
#     set_parser.add_argument("--outputdir", help="Set default output directory")
#     set_parser.add_argument("--reportname", help="Set default report name")
#     set_parser.add_argument("--popplerpath", help="Path to poppler/bin")
#     set_parser.add_argument("--txt_weightage", type=float, help="Text weightage (0.0 to 1.0)")
#     set_parser.add_argument("--text_threshold", type=float, help="Text similarity threshold (0.0 to 1.0)")
#     set_parser.add_argument("--visual_threshold", type=float, help="Visual similarity threshold (0.0 to 1.0)")
#     set_parser.add_argument("--ignore_patterns_flag", action="store_true", help="Enable or disable ignore patterns")
#     set_parser.add_argument("--semantic_threshold", help="Set default poppler path")
#     set_parser.add_argument("--semantic_max_phrase", help="Set default poppler path")

#     # --- COMMAND: reset-config ---
#     subparsers.add_parser("reset-config", help="Restore all configuration settings to factory defaults")

#     # --- COMMAND: ui ---
#     # subparsers.add_parser("ui", help="Launch the Streamlit Web Interface")

#     args = parser.parse_args()

#     # --- ROUTING LOGIC ---

#     # 1. DEFAULT DASHBOARD (Just typing 'verisift')
#     if args.command is None:
#         print("\n--- Verisift Engine v1.0 ---")
#         is_ok, _ = run_health_check()
#         status = "READY" if is_ok else "INCOMPLETE (run 'verisift health-check')"
#         print(f"System Health: {status}")
#         print("\nQuick Start: verisift run 'actual.pdf' 'expected.pdf'")
#         parser.print_help()
#         sys.exit(0)

#     # 2. HEALTH CHECK
#     if args.command == "health-check":
#         print("[*] Running System Dependency Check...")
#         is_ok, missing = run_health_check()
#         if is_ok:
#             print("[SUCCESS] All system dependencies (Poppler/Tesseract) are installed.")
#         else:
#             print("[ERROR] Missing the following system tools:")
#             for item in missing:
#                 print(f"  - {item}")
#             print("\nPlease install these via your OS package manager.")
#         sys.exit(0 if is_ok else 1)

#     # 3. RUN COMPARISON
#     elif args.command == "run":
#         # Check health silently before starting
#         is_ok, missing = run_health_check()
#         if not is_ok:
#             print(f"[ERROR] Cannot run. Missing dependencies: {', '.join(missing)}")
#             sys.exit(1)

#         # LOAD CONFIG: Layered priority (Default < User File < CLI Flags)
#         # Using type hint for better IDE support and code clarity
#         config: VerisiftConfig = cfg_mgr.load_user_config()
        
#         # Apply CLI overrides if provided
#         if args.mode: config.comparison_mode = args.mode
#         if args.dpi: config.dpi = args.dpi
#         if args.outputdir: config.output_dir = args.outputdir
#         if args.reportname: config.report_name = args.reportname

#         print(f"[*] Comparing: {os.path.basename(args.actual)} vs {os.path.basename(args.expected)}")
#         print(f"[*] Config: Mode={config.comparison_mode.upper()}, DPI={config.dpi}")

#         try:
#             comparator = Comparator(config)
#             report = comparator.compare(args.actual, args.expected)
            
#             os.makedirs(config.output_dir, exist_ok=True)
#             report_path = os.path.join(config.output_dir, config.report_name)
            
#             if generate_html_report(report, report_path):
#                 print(f"\n[SUCCESS] Report generated: {os.path.abspath(report_path)}")
#         except Exception as e:
#             print(f"[CRITICAL ERROR] {str(e)}")
#             sys.exit(1)

#     # 4. CONFIG MANAGEMENT
#     elif args.command == "display-config":
#         current_cfg = cfg_mgr.load_user_config()
#         print("\n--- Verisift Current Settings ---")
#         for key, value in current_cfg.__dict__.items():
#             print(f"{key:20}: {value}")
#         print("")

#     elif args.command == "set-config":
#         # Check if any configuration arguments were provided
#         config_args = [args.mode, args.dpi, args.outputdir, args.reportname, args.popplerpath, 
#                        args.txt_weightage, args.text_threshold, args.visual_threshold, args.ignore_patterns_flag]
        
#         if not any(arg is not None for arg in config_args):
#             print("[INFO] No changes specified. Use flags like --mode, --dpi, or --outputdir.")
#         else:
#             if args.mode: cfg_mgr.set_config("comparison_mode", args.mode)
#             if args.dpi: cfg_mgr.set_config("dpi", args.dpi)
#             if args.outputdir: cfg_mgr.set_config("output_dir", args.outputdir)
#             if args.popplerpath: cfg_mgr.set_config("poppler_path", args.popplerpath)
#             if args.ignore_patterns_flag is not None: cfg_mgr.set_config("ignore_patterns_flag", args.ignore_patterns_flag)
#             print("[SUCCESS] Global settings updated permanently.")

#     elif args.command == "reset-config":
#         if cfg_mgr.reset_to_defaults():
#             print("[SUCCESS] All settings restored to factory defaults.")
#         else:
#             print("[INFO] Settings were already at default values.")

#     # 5. STREAMLIT UI
#     elif args.command == "ui":
#         ui_path = os.path.join(os.path.dirname(__file__), "ui", "app.py")
#         if not os.path.exists(ui_path):
#             print("[ERROR] UI module not found.")
#             sys.exit(1)
        
#         print("[*] Launching Streamlit UI...")
#         subprocess.run(["streamlit", "run", ui_path])

# if __name__ == "__main__":
#     main()



import argparse
import sys
import os
import logging
from typing import Optional

# Internal Imports
from .config import VerisiftConfig
from .core import Comparator
from .utils.health import run_health_check
from .utils.config_manager import ConfigManager
from .pipeline.report import generate_html_report

# Initialize Logger
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

def main():
    cfg_mgr = ConfigManager()
    
    parser = argparse.ArgumentParser(
        prog="verisift",
        description="VeriSift: Professional PDF Comparison Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  verisift compare --actual a.pdf --expected e.pdf --mode semantic --dpi 300
  verisift set-config --popplerpath "C:\\poppler\\bin"
  verisift display-config
  verisift health-check
        """
    )
    
    parser.add_argument("-v", "--version", action="version", version="VeriSift v1.0")
    subparsers = parser.add_subparsers(dest="command", help="Available Commands")

    # --- HELPER: Common Configuration Arguments ---
    # This ensures both 'compare' and 'set-config' share the same flags
    def add_config_args(subparser, is_permanent=False):
        subparser.add_argument("--mode", choices=["literal", "semantic"], help="Comparison mode")
        subparser.add_argument("--dpi", type=int, help="Rendering DPI (50-300)")
        subparser.add_argument("--outputdir", help="Output directory path")
        subparser.add_argument("--reportname", help="Custom HTML report filename")
        subparser.add_argument("--popplerpath", help="Path to poppler/bin")
        subparser.add_argument("--txt_weightage", type=float, help="Text weightage (0.0 to 1.0)")
        subparser.add_argument("--text_threshold", type=float, help="Text similarity threshold (0.0 to 1.0)")
        subparser.add_argument("--visual_threshold", type=float, help="Visual similarity threshold (0.0 to 1.0)")
        subparser.add_argument("--semantic_threshold", type=float, help="Semantic match threshold (0.0 to 1.0)")
        subparser.add_argument("--semantic_max_phrase", type=int, help="Max words for semantic rephrasing")
        
        if is_permanent:
            subparser.add_argument("--ignore_patterns_flag", choices=["true", "false"], help="Enable/disable regex ignore patterns")
        else:
            subparser.add_argument("--ignore_patterns_flag", action="store_true", help="Enable ignore patterns for this run")

    # --- COMMAND: compare ---
    compare_parser = subparsers.add_parser("compare", help="Compare two PDF documents with optional overrides")
    compare_parser.add_argument("--actual", required=True, help="Path to actual PDF")
    compare_parser.add_argument("--expected", required=True, help="Path to expected PDF")
    add_config_args(compare_parser)

    # --- COMMAND: set-config ---
    set_parser = subparsers.add_parser("set-config", help="Update default settings permanently")
    add_config_args(set_parser, is_permanent=True)

    # --- COMMAND: health-check ---
    subparsers.add_parser("health-check", help="Verify Poppler/Dependency status")

    # --- COMMAND: display-config ---
    subparsers.add_parser("display-config", help="Show current persistent settings")

    # --- COMMAND: reset-config ---
    subparsers.add_parser("reset-config", help="Restore factory settings")

    args = parser.parse_args()

    # Mapping CLI arg names to VerisiftConfig attribute names
    config_mapping = {
        "mode": "comparison_mode",
        "enable_visual": "enable_visual",
        "dpi": "dpi",
        "outputdir": "output_dir",
        "reportname": "report_name",
        "popplerpath": "poppler_path",
        "txt_weightage": "txt_weightage",
        "text_threshold": "text_threshold",
        "visual_threshold": "visual_threshold",
        "semantic_threshold": "semantic_threshold",
        "semantic_max_phrase": "semantic_max_phrase",
        "ignore_patterns_flag": "ignore_patterns_flag"
    }

    # --- ROUTING LOGIC ---

    if args.command is None:
        print("\n--- VeriSift Engine v1.0 ---")
        is_ok, _ = run_health_check()
        print(f"System Status: {'READY' if is_ok else 'DEPENDENCIES MISSING'}")
        parser.print_help()
        sys.exit(0)

    elif args.command == "health-check":
        is_ok, missing = run_health_check()
        if is_ok:
            print("✅ System health is excellent. Poppler detected.")
        else:
            print(f"❌ Missing dependencies: {', '.join(missing)}")
        sys.exit(0 if is_ok else 1)

    elif args.command == "compare":
        config = cfg_mgr.load_user_config()
        
        # Apply one-off overrides from CLI
        for cli_key, attr_key in config_mapping.items():
            val = getattr(args, cli_key, None)
            if val is not None:
                setattr(config, attr_key, val)

        print(f"[*] Analyzing: {os.path.basename(args.actual)} vs {os.path.basename(args.expected)}")
        try:
            comparator = Comparator(config)
            report = comparator.compare(args.actual, args.expected)
            
            os.makedirs(config.output_dir, exist_ok=True)
            report_path = os.path.join(config.output_dir, config.report_name)
            
            if generate_html_report(report, report_path):
                logger.info(f"✅ Report generated: {os.path.abspath(report_path)}")
                print(f"✅ Comparison Finished. Report: {report_path}")
        except Exception as e:
            print(f"❌ Execution failed: {e}")
            sys.exit(1)

    elif args.command == "display-config":
        config = cfg_mgr.load_user_config()
        print("\n--- Current Configuration (User + Defaults) ---")
        for k, v in vars(config).items():
            print(f"{k:25}: {v}")

    elif args.command == "set-config":
        updated = False
        for cli_key, config_key in config_mapping.items():
            val = getattr(args, cli_key, None)
            if val is not None:
                cfg_mgr.set_config(config_key, val)
                logger.info(f"✅ Permanently set {config_key} to {val}")
                # print(f"✅ Permanently set {config_key} to {val}")
                updated = True
        
        if not updated:
            logger.warning("⚠️ No settings provided to update.")
            # print("⚠️ No settings provided to update.")

    elif args.command == "reset-config":
        if cfg_mgr.reset_to_defaults():
            logger.info("✅ Configuration reset to factory defaults.")
            # print("✅ Configuration reset to factory defaults.")
        else:
            logger.info("ℹ️ Already at default settings.")
            # print("ℹ️ Already at default settings.")

if __name__ == "__main__":
    main()