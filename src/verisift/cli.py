import argparse
import sys
import os
import logging
import re
import ast
from typing import Optional
from io import StringIO
import tokenize

# Internal Imports
from .config import VerisiftConfig
from .core import Comparator
from .utils.health import run_health_check
from .utils.config_manager import ConfigManager
from .pipeline.report import generate_html_report

# Initialize Logger
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

def _strip_string_literal(token_string: str) -> str:
    """
    Convert a Python-style string literal token into its content while preserving
    raw-string backslashes exactly as typed.
    
    For raw strings (r'...' or r"..."), returns the content with backslashes preserved.
    For regular strings, returns the content as-is (Python tokenizer already handles escapes).
    """
    token_string = token_string.strip()
    
    # Check if it's a raw string
    is_raw = False
    i = 0
    while i < len(token_string) and token_string[i].lower() in ("r", "u", "b", "f"):
        if token_string[i].lower() == 'r':
            is_raw = True
        i += 1

    if i >= len(token_string):
        return token_string

    quote = token_string[i]
    if quote not in ("'", '"'):
        return token_string

    # Handle triple-quoted strings
    if token_string[i:i + 3] in ("'''", '"""'):
        q = token_string[i:i + 3]
        content = token_string[i + 3:-3] if token_string.endswith(q) else token_string
        return content

    # Handle single/double quoted strings
    content = token_string[i + 1:-1] if token_string.endswith(quote) else token_string
    
    # For raw strings, the content is already correct (backslashes preserved)
    # For regular strings, Python's tokenizer has already processed escape sequences
    return content


def _manual_parse_patterns(list_content: str) -> list:
    """
    Manually parse string literals from list content when tokenizer fails.
    Handles both single and double quoted strings with r-prefix support.
    """
    patterns = []
    i = 0
    while i < len(list_content):
        # Skip whitespace and commas
        while i < len(list_content) and list_content[i] in ' ,\t\n':
            i += 1
        
        if i >= len(list_content):
            break
        
        # Check for r-prefix
        is_raw = False
        if i < len(list_content) and list_content[i].lower() == 'r':
            is_raw = True
            i += 1
        
        # Determine quote type
        if i >= len(list_content):
            break
            
        quote_char = list_content[i]
        if quote_char not in ('"', "'"):
            i += 1
            continue
        
        # Find matching closing quote
        i += 1
        start = i
        while i < len(list_content):
            if list_content[i] == '\\' and not is_raw:
                # Skip escaped character
                i += 2
                continue
            elif list_content[i] == quote_char:
                # Found closing quote
                pattern = list_content[start:i]
                patterns.append(pattern)
                i += 1
                break
            else:
                i += 1
    
    return patterns


def _tokenize_pattern_list(list_content: str) -> list:
    """
    Tokenize the inner content of a Python-style list and extract only string
    literal items without splitting on commas inside regex quantifiers.
    """
    patterns = []

    try:
        tokens = tokenize.generate_tokens(StringIO(list_content).readline)
        for tok_type, tok_string, _, _, _ in tokens:
            if tok_type == tokenize.STRING:
                stripped = _strip_string_literal(tok_string)
                patterns.append(stripped)
                print(f"  Tokenized pattern: {stripped}")
    except tokenize.TokenError as e:
        logger.warning(f"Tokenize error: {e}. Attempting manual parsing.")
        # Fallback: manually parse string literals
        patterns = _manual_parse_patterns(list_content)
        for p in patterns:
            print(f"  Manually parsed pattern: {p}")

    return patterns


def _parse_exclusion_patterns(val) -> list:
    """
    Parse CLI exclusion patterns while preserving regex text exactly as typed.
    Handles both single string and list inputs from argparse.
    """
    # If val is already a list (from nargs="+"), process the first element
    # which should be the Python list string format
    if isinstance(val, list):
        if len(val) == 0:
            return []
        # If it's a list with one element that looks like a Python list, parse it
        if len(val) == 1 and isinstance(val[0], str):
            val = val[0]
        else:
            # Multiple space-separated patterns - return as-is
            return val
    
    if not isinstance(val, str):
        return [val]

    cleaned = val.strip()

    if cleaned.startswith('[') and cleaned.endswith(']'):
        inner = cleaned[1:-1].strip()
        if not inner:
            return []
        print(f"inner: {inner}")
        parsed = _tokenize_pattern_list(inner)
        if parsed:
            return parsed

        logger.warning("Failed to parse exclusion patterns as a list of string literals")
        return [cleaned]

    lowered = cleaned[:2].lower()
    if lowered in ('r"', "r'"):
        return [_strip_string_literal(cleaned)]
    if cleaned.startswith(('"', "'")):
        return [_strip_string_literal(cleaned)]

    return [cleaned]

def main():
    cfg_mgr = ConfigManager()
    
    parser = argparse.ArgumentParser(
        prog="verisift",
        description="VeriSift: Professional PDF Comparison Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  verisift compare --actual a.pdf --expected e.pdf --mode semantic --dpi 150
  verisift set-config --popplerpath "C:\\Program Files\\poppler\\Library\\bin"
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
        subparser.add_argument("--enable_visual", choices=["true", "false"], help="Enable visual comparison")
        subparser.add_argument("--dpi", type=int, help="Rendering DPI (50-300)")
        subparser.add_argument("--outputdir", help="Output directory path")
        subparser.add_argument("--reportname", help="Custom HTML report filename")
        subparser.add_argument("--popplerpath", help="Path to poppler/bin")
        subparser.add_argument("--txt_weightage", type=float, help="Text weightage (0.0 to 1.0)")
        subparser.add_argument("--text_threshold", type=float, help="Text similarity threshold (0.0 to 1.0)")
        subparser.add_argument("--visual_threshold", type=float, help="Visual similarity threshold (0.0 to 1.0)")
        subparser.add_argument("--semantic_threshold", type=float, help="Semantic match threshold (0.0 to 1.0)")
        subparser.add_argument("--semantic_max_phrase", type=int, help="Max words for semantic rephrasing")
        subparser.add_argument("--exclusion_patterns", nargs="+", help="Regex patterns to exclude (space-separated or Python list format)")
        
        if is_permanent:
            subparser.add_argument("--enable_exclusions", choices=["true", "false"], help="Enable/disable regex ignore patterns")
        else:
            subparser.add_argument("--enable_exclusions", action="store_true", help="Enable ignore patterns for this run")

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
        "enable_exclusions": "ignore_patterns_flag",
        "exclusion_patterns": "ignore_patterns"
    }

    # listing out cli keys which accepts only bool values
    bool_cli_key = ["enable_exclusions", "enable_visual"]
    
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
            logger.info("✅ System health is excellent. Poppler detected.")
            # print("✅ System health is excellent. Poppler detected.")
        else:
            logger.error(f"❌ Missing dependencies: {', '.join(missing)}")
            # print(f"❌ Missing dependencies: {', '.join(missing)}")
        sys.exit(0 if is_ok else 1)

    elif args.command == "compare":
        config = cfg_mgr.load_user_config()
        
        # Apply one-off overrides from CLI
        for cli_key, attr_key in config_mapping.items():
            val = getattr(args, cli_key, None)
            if val is not None:
                # Handle complex regex parsing
                if cli_key == "exclusion_patterns":
                    val = _parse_exclusion_patterns(val)
                    print(f"list of values for patterns: {val}")
                
                if cli_key in bool_cli_key:
                    if str(val).lower() == 'true':
                        val = True
                    if str(val).lower() == 'false':
                        val = False
                setattr(config, attr_key, val)

        print(f"[*] Analyzing: {os.path.basename(args.actual)} vs {os.path.basename(args.expected)}")
        try:
            comparator = Comparator(config)
            report = comparator.compare(args.actual, args.expected)
            
            os.makedirs(config.output_dir, exist_ok=True)
            report_path = os.path.join(config.output_dir, config.report_name)
            
            if generate_html_report(report, report_path):
                logger.info(f"✅ Comparison Finished. Report generated successfully at: {os.path.abspath(report_path)}")
                # print(f"✅ Comparison Finished. Report: {report_path}")
        except Exception as e:
            logger.error(f"❌ Execution failed: {e}")
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
                # Handle complex regex parsing
                if cli_key == "exclusion_patterns":
                    val = _parse_exclusion_patterns(val)

                if cli_key in bool_cli_key:
                    if str(val).lower() in ['true', 'false']:
                        val = str(val).lower() == 'true'
                        
                cfg_mgr.set_config(config_key, val)
                logger.info(f"✅ Permanently set {config_key} to {val}")
                # print(f"✅ Permanently set {config_key} to {val}")
                updated = True
        
        if not updated:
            logger.warning("⚠️ No settings provided to update.")

    elif args.command == "reset-config":
        if cfg_mgr.reset_to_defaults():
            logger.info("✅ Configuration reset to factory defaults.")
            # print("✅ Configuration reset to factory defaults.")
        else:
            logger.info("ℹ️ Already at default settings.")

if __name__ == "__main__":
    main()