# VeriSift/src/verisift/models.py
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import numpy as np

@dataclass
class PageComparisonResult:
    """
    Detailed Explanation:
    This object stores the complete 'Audit Trail' for a single page. 
    It combines the text analysis, the visual analysis, and the final status.
    """
    page_index: int
    
    # --- Text Results ---
    text_score: float        # Literal score (0.0 - 1.0)
    text_match: bool         # True if score >= threshold
    # diff_text: str           # The +/- character diff for the report
    expected_diff_html: str 
    actual_diff_html: str
    
    # --- Visual Results ---
    visual_score: float      # SSIM score (0.0 - 1.0)
    visual_match: bool       # True if score >= threshold
    # np.ndarray: The OpenCV 'Heatmap' image showing pixel changes
    # storing this so the Report Generator can save it as a PNG later.
    heatmap: Optional[np.ndarray] = None 

    actual_image: Optional[np.ndarray] = None
    expected_image: Optional[np.ndarray] = None

    # --- Intent Results ---
    intent_score: Optional[float] = None # Semantic score (0.0 - 1.0)
    semantic_diff_expected_html: Optional[str] = None
    semantic_diff_actual_html: Optional[str] = None

    # --- Metadata & Flags ---
    is_scanned: bool = False # From ingest.py logic
    error_message: Optional[str] = None # If a specific page fails to process

@dataclass
class ComparisonReport:
    """
    Detailed Explanation:
    The top-level object representing the entire comparison session. 
    This is what the UI and the Report Generator will consume.
    """
    actual_path: str
    expected_path: str
    
    # Configuration to display on the report
    configuration: Dict[str, Any]

    # List: A collection of PageComparisonResult objects
    pages: List[PageComparisonResult] = field(default_factory=list)

    # OVerall matching score
    overall_score: float = 0.0
    
    
    # --- Global Summary Statistics ---
    # Why: Great for a "Dashboard" view in the UI (e.g. "8/10 pages passed")
    total_pages: int = 0
    passed_pages: int = 0
    failed_pages: int = 0

    # text score
    text_score_avg: float = 0.0

    # visual score
    visual_score_avg: Optional[float] = None

    # Intent matching score
    avg_intent_score: Optional[float] = None

    # Metadata about the PDF
    metadata: Dict[str, Any] = field(default_factory=lambda: {"actual": {}, "expected": {}})
