# VERIDOC/src/veridoc/config.py
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class VerisiftConfig:
    # Textual and Visual weightage
    # textual weightage lies in the range 0.0 to 1.0, 
    # visual weightage is automatically caluclated by 1-textual weightage
    txt_weightage: float = 0.8 # for more textual content and less visual content
    
    # Thresholds for similarity (0.0 to 1.0)
    # --- Similarity Sensitivity ---
    # float: 0.95 means 95% semantic match required to 'pass'
    text_threshold: float = 0.95  # 0.95 will give the threshold to ignore small changes like extra space, a slightly different encoding of a character
    # float: 0.98 means 98% pixel-structure match required to 'pass'
    visual_threshold: float = 0.98 # 0.98 will give the threshold to look at patterns, luminance, and contrast to see if the structure of the page has changed
    
    # --- Comparison Strategy ---
    # str: 'literal' for word-to-word, 'semantic' for intent-based (AI)
    # Why: This allows the user to switch between "Strict" (literal) and "Smart"(semantic) modes.
    comparison_mode: str = "literal" # accepted values: "literal" / "semantic"

    # Rendering settings
    # --- Ingestion & Rendering ---
    # int: Dots Per Inch
    dpi: int = 150  # Lower for speed, higher for precision (max 300)
    
    # Exclusions
    # list: Uses Regex patterns to strip dynamic text (dates, IDs) before comparison
    ignore_patterns_flag: bool = field(default=False) # checks for the flag initially to proceed with exclusions
    ignore_patterns: List[str] = field(default_factory= list) # List is empty by default

    # Path to poppler - if the user has poppler in different path, then the config vairable can be updated in order to let the code pick the poppler
    poppler_path: str = r"C:\Program Files\poppler\Library\bin"
    
    # Output
    # str: Default filename for the portable HTML report
    report_name: str = "veridoc_report.html"
    output_dir: str = "reports"
    
    # Feature Toggles
    enable_nlp: bool = True
    enable_visual: bool = True

    # "Sensitivity Dial" - settings that control the sematic comparison behaviour
    semantic_threshold: float = 0.5  # High precision for Legal, Contracts, Official documents
    semantic_max_phrase: int = 20      # Check for rephrased multi-word terms, this decides the length of the phrase that the semantic compare applies
    enable_intent_summary: bool = True # Flag for the "Overall Page Meaning" check

    # OCR Logic
    # bool: If True, Verisift will attempt to extract text from images/scanned pages.
    # Why: This allows the engine to handle PDFs that don't have 'selectable' text.
    ocr_enabled: bool = False