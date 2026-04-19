# VERIDOC/src/veridoc/config.py
from dataclasses import dataclass, field
from typing import List, Optional
import os
import getpass
from datetime import datetime
import json

@dataclass
class VerisiftConfig:
    # Textual and Visual weightage for overall score calculation
    # textual weightage lies in the range 0.0 to 1.0, 
    # visual weightage is automatically caluclated by 1-textual weightage
    # if textual_weightage is set to 0.4 then the overall score calculation will be \
    # (0.4*textual score) + ((1-0.4)*(visual score)) 
    # set it to 0.5 if you wish to have equal weightage to both text and visual score
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
    report_name: str = f"verisift_report_{datetime.now().strftime('%Y-%m-%d_%H.%M.%S')}.html"
    output_dir: str = field(default=os.path.join("C:\\Users", getpass.getuser(), \
            "Downloads", "verisift"))
    
    # Feature Toggles
    # enable_nlp: bool = True
    enable_visual: bool = True

    # "Sensitivity Dial" - settings that control the sematic comparison behaviour
    semantic_threshold: float = 0.8  # High precision for Legal, Contracts, Official documents
    semantic_max_phrase: int = 20      # Check for rephrased multi-word terms, this decides the length of the phrase that the semantic compare applies
    # enable_intent_summary: bool = True # Flag for the "Overall Page Meaning" check

    # OCR Logic
    # bool: If True, Verisift will attempt to extract text from images/scanned pages.
    # Why: This allows the engine to handle PDFs that don't have 'selectable' text.
    # ocr_enabled: bool = False



    # Inside VerisiftConfig class in config.py

CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".verisift_config.json")

def save_to_disk(self):
    """Saves the current dataclass state to a JSON file."""
    # We exclude report_name because it's timestamped and shouldn't be 'permanent'
    data = {k: v for k, v in self.__dict__.items() if k != 'report_name'}
    with open(CONFIG_FILE, 'w') as f:
        json.dump(data, f, indent=4)

@classmethod
def load_from_disk(cls):
    """Creates a config object using saved disk settings as defaults."""
    instance = cls()
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                saved_data = json.load(f)
                for key, value in saved_data.items():
                    if hasattr(instance, key):
                        setattr(instance, key, value)
        except Exception as e:
            print(f"Warning: Could not load saved config: {e}")
    return instance