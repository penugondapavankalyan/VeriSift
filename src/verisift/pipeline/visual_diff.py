# VeriSift/src/verisift/pipeline/visual_diff.py
import logging
import cv2  # OpenCV
import numpy as np
from skimage.metrics import structural_similarity as ssim
from ..config import VerisiftConfig

logger = logging.getLogger(__name__)

def _align_images(image_a, image_b):
    """Aligns Image B to Image A using ECC algorithm."""
    gray_a = cv2.cvtColor(image_a, cv2.COLOR_BGR2GRAY)
    gray_b = cv2.cvtColor(image_b, cv2.COLOR_BGR2GRAY)

    warp_mode = cv2.MOTION_EUCLIDEAN
    warp_matrix = np.eye(2, 3, dtype=np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 50, 1e-7)

    try:
        _, warp_matrix = cv2.findTransformECC(gray_a, gray_b, warp_matrix, warp_mode, criteria)
        aligned_b = cv2.warpAffine(image_b, warp_matrix, (image_a.shape[1], image_a.shape[0]), 
                                    flags=cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP)
        return aligned_b
    except cv2.error:
        logger.warning("Alignment failed. Using original images.")
        return image_b

def compare_visual(image_a: np.ndarray, image_b: np.ndarray, config: VerisiftConfig):
    """
    Performs visual comparison and generates a COLOR Heatmap.
    image_a: Target (Actual)
    image_b: Baseline (Expected)
    """
    # 1. Align and ensure same dimensions
    image_b_aligned = _align_images(image_a, image_b)
    if image_a.shape != image_b_aligned.shape:
        image_b_aligned = cv2.resize(image_b_aligned, (image_a.shape[1], image_a.shape[0]))

    # 2. SSIM Score Calculation (Grayscale)
    gray_a = cv2.cvtColor(image_a, cv2.COLOR_BGR2GRAY)
    gray_b = cv2.cvtColor(image_b_aligned, cv2.COLOR_BGR2GRAY)
    score, _ = ssim(gray_a, gray_b, full=True)

    # 3. COLOR HEATMAP GENERATION
    # Create a faded version of the original image as a background context
    canvas = cv2.addWeighted(image_a, 0.1, np.full(image_a.shape, 255, dtype=np.uint8), 0.9, 0)

    # Calculate absolute difference
    # Using bitwise operations to find distinct pixels
    _, mask_a = cv2.threshold(gray_a, 200, 255, cv2.THRESH_BINARY_INV)
    _, mask_b = cv2.threshold(gray_b, 200, 255, cv2.THRESH_BINARY_INV)

    # Pixels in Actual but NOT in Expected (Additions -> Red)
    added = cv2.bitwise_and(mask_a, cv2.bitwise_not(mask_b))
    # Pixels in Expected but NOT in Actual (Missing -> Blue)
    missing = cv2.bitwise_and(mask_b, cv2.bitwise_not(mask_a))

    # Clean up noise
    kernel = np.ones((2,2), np.uint8)
    added = cv2.morphologyEx(added, cv2.MORPH_OPEN, kernel)
    missing = cv2.morphologyEx(missing, cv2.MORPH_OPEN, kernel)

    # Apply colors to the canvas
    # BGR format: Red is (0, 0, 255), Blue is (255, 0, 0)
    canvas[added > 0] = [0, 0, 255]    # Additions in Red
    canvas[missing > 0] = [255, 0, 0]  # Missing in Blue

    # 4. Packaging
    is_match = score >= config.visual_threshold
    logger.debug(f"Visual Similarity Score: {score:.4f}")

    return {
        "vis_score": round(score, 4),
        "is_match": is_match,
        "heatmap": canvas  # Now returns a BGR color image
    }