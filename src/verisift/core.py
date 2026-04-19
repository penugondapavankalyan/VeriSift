# VeriSift/src/verisift/core.py
import logging 
import os 
from .config import VerisiftConfig # settings dataclass
from .pipeline.ingest import ingest_pdf # PDF reading engine
from .pipeline.text_diff import compare_text
from .pipeline.visual_diff import compare_visual
from .pipeline.report import generate_html_report
from .models import PageComparisonResult, ComparisonReport
from itertools import zip_longest

# 1. THE LOGGING SETUP FUNCTION
def setup_logging(output_dir="logs", log_to_file=True):
    """
    'Comparator' can call this function to set up logging for the entire application.
    Why: This centralizes logging configuration and ensures that all logs are captured consistently across modules.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    log_format = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    handlers = [logging.StreamHandler()] 
    
    if log_to_file:
        log_file = os.path.join(output_dir, "verisift.log")
        handlers.append(logging.FileHandler(filename=log_file))

    # This 'basicConfig' applies to ALL modules in your project
    logging.basicConfig(
        level=logging.INFO, 
        format=log_format,
        handlers=handlers
    )

# 2. INITIALIZE MODULE LOGGER
# Why: This logger belongs specifically to the 'core' module
logger = logging.getLogger(__name__)

# 3. THE ORCHESTRATOR CLASS
class Comparator:
    def __init__(self, config: VerisiftConfig = None):
        """
        Detailed Explanation:
        The constructor is the first thing that runs. 
        It sets up the config and the logs.
        """
        # Step A: Load Config
        self.config = config or VerisiftConfig()
        logger.info(f"Verisift Comparator initialized with config: {self.config}")
        # Step B: Setup Logging using the function we defined above
        setup_logging(output_dir="logs", log_to_file=True)
        
        # Step C: Create required folders (Environment check)
        self._initialize_environment()
        
        logger.info("-----------------Verisift Comparator initialized and ready-----------------")

    def _initialize_environment(self):
        """
        Ensures the 'reports' folder exists so it doesn't crash 
        when trying to save the final HTML.
        """
        if not os.path.exists(self.config.output_dir):
            os.makedirs(self.config.output_dir)
            logger.info(f"Created output directory: {self.config.output_dir}")
    
    def is_image_pdf(self, doc_actual, doc_expected):
        """
        Checks if either document is an 'Image-PDF' (scanned document).
        Why: Evaluates page metadata to decide between semantic or visual-only diffing.
        """
        # 1. Create lists of booleans (True/False) for each page
        actual_scan_results = [p.is_scanned for p in doc_actual.pages]
        expected_scan_results = [p.is_scanned for p in doc_expected.pages]
        
        # 2. Log specific pages for debugging
        for i, is_scanned in enumerate(actual_scan_results):
            if is_scanned:
                logger.debug(f"Actual document - Page {i+1} detected as scanned image.")

        for i, is_scanned in enumerate(expected_scan_results):
            if is_scanned:
                logger.debug(f"Expected document - Page {i+1} detected as scanned image.")

        # 3. Create the final decision dictionary
        doc_is_image = {
            "doc_actual_is_image": all(actual_scan_results),
            "doc_expected_is_image": all(expected_scan_results)
        }
        
        logger.info(f"Scan detection complete: {doc_is_image}")
        return doc_is_image
    def overall_score_calculator(self, txt_diff_score: float, visual_diff_score: float) -> float:
        txt_score = self.config.txt_weightage * txt_diff_score
        visual_score = (1 - self.config.txt_weightage) * visual_diff_score
        return txt_score + visual_score
    
    def validate_config(self) -> bool:
        """
        Checks if the config is valid. Raises an exception if invalid.
        """
        valid_config = [True]
        if not self.config:
            valid_config.append(False)
            raise ValueError("No config provided.")
        
        if self.config.txt_weightage < 0 or self.config.txt_weightage > 1:
            valid_config.append(False)
            logger.error(f"Text weightage must be between 0 and 1 but it is {self.config.txt_weightage}")
            raise ValueError("Text weightage must be between 0 and 1.")

        if self.config.text_threshold < 0 or self.config.text_threshold > 1:
            valid_config.append(False)
            logger.error(f"Text similarity threshold must be between 0 and 1 but it is {self.config.text_threshold}")
            raise ValueError("Text similarity threshold must be between 0 and 1.")
        
        if self.config.visual_threshold < 0 or self.config.visual_threshold > 1:
            valid_config.append(False)
            logger.error(f"Visual similarity threshold must be between 0 and 1 but it is {self.config.visual_threshold}")
            raise ValueError("Visual similarity threshold must be between 0 and 1.")
        
        if self.config.comparison_mode not in ["literal", "semantic"]:
            valid_config.append(False)
            logger.error(f"Invalid comparison mode: {self.config.comparison_mode}. Must be 'literal' or 'semantic'.")
            raise ValueError("Invalid comparison mode. Must be 'literal' or 'semantic'.")
        
        if self.config.dpi < 50 or self.config.dpi > 300:
            valid_config.append(False)
            logger.error(f"Invalid DPI value: {self.config.dpi}. Must be between 50 and 300.")
            raise ValueError("Invalid DPI value. Must be between 50 and 300.")
        
        if self.config.ignore_patterns_flag and not isinstance(self.config.ignore_patterns, list):
            valid_config.append(False)
            logger.error(f"Invalid ignore_patterns value: {self.config.ignore_patterns}. Must be a list if ignore_patterns_flag is True.")
            raise ValueError("Invalid ignore_patterns value. Must be a list if ignore_patterns_flag is True.")
        
        if self.config.comparison_mode=="semantic":
            if self.config.semantic_threshold < 0 or self.config.semantic_threshold > 1:
                valid_config.append(False)
                logger.error(f"Invalid semantic threshold value: {self.config.semantic_threshold}. Must be between 0 and 1.")
                raise ValueError("Invalid semantic threshold value. Must be between 0 and 1.")
            if self.config.semantic_max_phrase < 1 or self.config.semantic_max_phrase > 100:
                valid_config.append(False)
                logger.error(f"Invalid semantic max phrase value: {self.config.semantic_max_phrase}. Must be between 1 and 100.")
                raise ValueError("Invalid semantic max phrase value. Must be between 1 and 100.")
        
        return all(valid_config)


    def compare(self, actual_path: str, expected_path: str) -> ComparisonReport:
        """
        The Main Pipeline Workflow.
        """
        logger.info(f"validating configuration...")
        validate_config_result = self.validate_config()
        if validate_config_result:
            logger.info(f"Configuration is valid...")
        else:
            logger.error(f"Configuration is invalid...")
            raise ValueError("Configuration is invalid.")
        

        logger.info(f"Starting comparison: {actual_path} vs {expected_path}")

        # Step 1: Ingestion (Returns DocumentData objects)
        doc_actual = ingest_pdf(actual_path, self.config)
        doc_expected = ingest_pdf(expected_path, self.config)

        # Step 2: Basic Validation (Length Check)
        if len(doc_actual.pages) != len(doc_expected.pages):
            logger.warning(
                f"Page count mismatch! Actual: {len(doc_actual.pages)}, "
                f"Expected: {len(doc_expected.pages)}"
            )

        # Step 3: Decision Gate (Image-PDF Check)
        # doc_is_image = self.is_image_pdf(doc_actual, doc_expected)

        # if doc_is_image["doc_actual_is_image"]:
            # logger.warning("Actual PDF contains scanned images. Semantic diffing may be limited.")
            # if self.config.ocr_enabled:
            #     logger.info("Scanned pages detected. Initializing OCR engine...")
            # # self.run_ocr_pipeline(doc_actual)
            # else:
            #     logger.warning(
            # "Scanned pages detected but OCR is disabled. "
            # "Falling back to Visual (Pixel) comparison only."
            #     )
        # if doc_is_image["doc_expected_is_image"]:
        #     logger.warning("Expected PDF contains scanned images. Semantic diffing may be limited.")
        #     if self.config.ocr_enabled:
        #         logger.info("Scanned pages detected. Initializing OCR engine...")
        #         # self.run_ocr_pipeline(doc_expected)
        #     else:
        #         logger.warning(
        #             "Scanned pages detected but OCR is disabled. "
        #             "Falling back to Visual (Pixel) comparison only."
        #             )
        
        # Step 4: text_diff and visual_diff 


        # 1. Initialize Report with Metadata
        # Capture basic file stats to show in the "Document Metadata" card
        report = ComparisonReport(
            actual_path=actual_path,
            expected_path=expected_path,
            configuration=vars(self.config),
            total_pages=max(len(doc_actual.pages), len(doc_expected.pages)),
            metadata={
                "actual": {
                    "filename": os.path.basename(actual_path),
                    "filesize": f"{os.path.getsize(actual_path) / 1024:.1f} KB",
                },
                "expected": {
                    "filename": os.path.basename(expected_path),
                    "filesize": f"{os.path.getsize(expected_path) / 1024:.1f} KB",
                }
            }
        )

        # 2. Iterate through pages using zip_longest
        # fillvalue=None ensures that if one document ends, the loop continues with None for that page
        for i, (page_a, page_b) in enumerate(zip_longest(doc_actual.pages, doc_expected.pages, fillvalue=None)):
            logger.info(f"Analyzing Page {i+1}...")

            # Define defaults for missing pages
            # If page_a is None, the actual PDF is shorter than the expected one
            # If page_b is None, the actual PDF has an extra page (your current case)
            
            # --- A. Text Analysis ---
            if page_a and page_b:
                text_res = compare_text(page_a.clean_text, page_b.clean_text, self.config)
                if self.config.enable_visual:
                    vis_res = compare_visual(page_a.image, page_b.image, self.config)
                else:
                    vis_res = None
                is_scanned = page_a.is_scanned or page_b.is_scanned
                actual_img = page_a.image
                expected_img = page_b.image
            else:
                # Handle Mismatched Page (One is missing)
                # We provide an empty comparison table if a page is missing
                txt_a = page_a.clean_text if page_a else ""
                txt_b = page_b.clean_text if page_b else ""

                # text_res = {"score": 0.0, "is_match": False, "diff_text": "PAGE MISSING IN COMPARISON"}
                # text_res = {"score": 0.0, "is_match": False, "diff_text": page_a.clean_text if page_a else page_b.clean_text}
                # Still call compare_text so the HTML table is generated correctly
                text_res = compare_text(txt_a, txt_b, self.config)
                logger.info("compare successful...")
                text_res["text_score"] = 0.0
                text_res["is_match"] = False
                vis_res = {"vis_score": 0.0, "is_match": False, "heatmap": None} if self.config.enable_visual else None
               # Heatmap generator usually needs 2 images
                is_scanned = False
                actual_img = page_a.image if page_a else None
                expected_img = page_b.image if page_b else None

            # --- C. Package Result ---
            # Using the dataclass ensures type-safety for the UI/Report
            page_result = PageComparisonResult(
                page_index=i,
                text_score=text_res["text_score"],
                intent_score=text_res["intent_score"],
                text_match=text_res["is_match"],
                actual_diff_html=text_res["actual_diff_html"],
                expected_diff_html=text_res["expected_diff_html"],
                semantic_diff_actual_html=text_res["semantic_diff_actual_html"],
                semantic_diff_expected_html=text_res["semantic_diff_expected_html"],
                visual_score=vis_res["vis_score"] if (vis_res and self.config.enable_visual) else None,
                visual_match=vis_res["is_match"] if (vis_res and self.config.enable_visual) else None,
                heatmap=vis_res["heatmap"] if (vis_res and self.config.enable_visual) else None,
                actual_image=actual_img if self.config.enable_visual else None,
                expected_image=expected_img if self.config.enable_visual else None,
                is_scanned=is_scanned
            )

            # Update master report
            report.pages.append(page_result)
            
            # Update counters for the final summary (Logic depends on whether visual is enabled)
            is_page_pass = page_result.text_match
            if self.config.enable_visual:
                is_page_pass = is_page_pass and page_result.visual_match
            
            if is_page_pass: report.passed_pages += 1
            else: report.failed_pages += 1

        # Calculate the Final Overall Score
        # This gives a single 'matching similarity %' for the entire document
        if report.total_pages > 0:
            # Average of text and visual scores across all pages
            report.text_score_avg = sum(p.text_score for p in report.pages) / len(report.pages)
            if self.config.enable_visual:
                report.visual_score_avg = sum(p.visual_score for p in report.pages) / len(report.pages)
            else:
                report.visual_score_avg = None
            
            if self.config.comparison_mode == "semantic":
                report.avg_intent_score = round((sum(p.intent_score for p in report.pages) / len(report.pages))*100 , 2)
            else:
                report.avg_intent_score = None

            # report.overall_score = round(((avg_text + avg_vis) / 2) * 100, 2)
            report.overall_score = round(self.overall_score_calculator(report.text_score_avg, report.visual_score_avg) * 100, 2) if self.config.enable_visual else round(report.text_score_avg * 100, 2)

            report.failed_pages = report.total_pages - report.passed_pages
            logging.info(f"{report.passed_pages} page(s) PASSED, {report.failed_pages} page(s) FAILED")

        else:
            report.overall_score = 0.0

        logger.info(f"Comparison Summary: {report.passed_pages}/{report.total_pages} pages passed.")
        logger.info(f"Overall Score: {report.overall_score}%")
        return report # Return the full data object 


    def generate_report(self, actual_path: str, expected_path: str, \
            output_path: str=os.path.join(VerisiftConfig.output_dir, \
            VerisiftConfig.report_name)):
        try:
            report = self.compare(actual_path, expected_path)
            # print(f"verisift.core:report info: {report}")
            generate_html_report(report, output_path)
        
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            raise e