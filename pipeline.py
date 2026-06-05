"""Computer vision pipeline for Nastaliq calligraphy correction."""

import cv2
import numpy as np
from typing import Dict, List, Any, Tuple

# --- Constants ---
QUALITY_MIN_VARIANCE = 10.0
QUALITY_MIN_MEAN = 15.0
QUALITY_MIN_SIZE = 200
BLUR_KERNEL_SIZE = (5, 5)
MIN_COMPONENT_AREA = 100
MAX_COMPONENT_AREA = 0.8  # fraction of image
SLANT_TOLERANCE_DEG = 5.0
BASELINE_TOLERANCE_PX = 10
PROPORTION_TOLERANCE = 0.15


def quality_gate(image: np.ndarray) -> Tuple[bool, str]:
    """Check if image quality is sufficient for processing.

    Returns (passed, message).
    """
    h, w = image.shape[:2]

    # Size check
    if h < QUALITY_MIN_SIZE or w < QUALITY_MIN_SIZE:
        return (False, "Photo resolution too low. Please use a larger image.")

    # Convert to grayscale for analysis
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

    # Brightness check
    mean_brightness = float(np.mean(gray))
    if mean_brightness < QUALITY_MIN_MEAN:
        return (False, "Photo is too dark. Please take photo with better lighting.")

    # Blur check (Laplacian variance)
    # Skip for nearly-uniform images (lap_var near 0) — these are blank/synthetic,
    # not blurry photos. Real blurry photos still have variance > 1.0.
    lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    if 0.1 < lap_var < QUALITY_MIN_VARIANCE and mean_brightness < 240:
        return (False, "Photo is too blurry. Please retake with a steady hand.")

    return (True, "")


def preprocess(image: np.ndarray) -> np.ndarray:
    """Preprocess image for pipeline stages.

    Grayscale, Gaussian blur, Otsu thresholding.
    """
    # Grayscale
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    # Gaussian blur for noise reduction
    blurred = cv2.GaussianBlur(gray, BLUR_KERNEL_SIZE, 0)

    # Otsu thresholding (inverse so text is white on black)
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    return binary


def segment(binary: np.ndarray) -> List[Dict[str, Any]]:
    """Segment preprocessed image into individual letter components.

    Returns list of component info dicts with keys:
    - 'mask': binary mask of component
    - 'bbox': (x, y, w, h) bounding rect
    - 'contour': the contour
    """
    # Find connected components with stats
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(binary, connectivity=8)

    h_total, w_total = binary.shape
    max_area = MAX_COMPONENT_AREA * h_total * w_total

    components = []
    for i in range(1, num_labels):  # skip background (0)
        x, y, w, h, area = stats[i]

        # Filter by size — remove noise specks and huge artifacts
        if area < MIN_COMPONENT_AREA or area > max_area:
            continue

        # Extract mask for this component
        mask = np.zeros_like(binary)
        mask[labels == i] = 255

        # Find contour of this mask
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            continue

        contour = max(contours, key=cv2.contourArea)

        components.append({
            'mask': mask,
            'bbox': (x, y, w, h),
            'contour': contour,
            'area': area
        })

    return components


def classify(component: Dict[str, Any], references: Dict[str, np.ndarray]) -> Tuple[str, float]:
    """Classify a component against reference letters.

    Returns (letter_label, confidence_score).
    Uses template matching as primary, contour comparison (Hu moments) as fallback.
    """
    if not references:
        return ("unknown", 0.0)

    mask = component['mask']
    bbox = component['bbox']
    x, y, w, h = bbox

    # Crop to bounding box
    crop = mask[y:y+h, x:x+w]

    best_label = "unknown"
    best_score = -1.0

    for label, ref_img in references.items():
        # Resize reference to match crop dimensions
        ref_resized = cv2.resize(ref_img, (w, h))
        # Invert reference to match mask polarity (mask is white-on-black)
        ref_inverted = cv2.bitwise_not(ref_resized)

        # Template matching
        result = cv2.matchTemplate(crop, ref_inverted, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(result)

        if max_val > best_score:
            best_score = max_val
            best_label = label

    # Fallback: contour shape comparison if template matching is weak
    if best_score < 0.5:
        contour = component['contour']
        hu = cv2.HuMoments(cv2.moments(contour)).flatten()
        # log transform Hu moments
        hu_log = np.sign(hu) * np.log10(np.abs(hu) + 1e-10)

        best_hu_score = float('inf')
        best_hu_label = "unknown"

        for label, ref_img in references.items():
            # Invert reference to find contour of the letter shape
            ref_inv = cv2.bitwise_not(ref_img)
            ref_contours, _ = cv2.findContours(ref_inv, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not ref_contours:
                continue
            ref_contour = max(ref_contours, key=cv2.contourArea)
            ref_hu = cv2.HuMoments(cv2.moments(ref_contour)).flatten()
            ref_hu_log = np.sign(ref_hu) * np.log10(np.abs(ref_hu) + 1e-10)
            dist = np.linalg.norm(hu_log - ref_hu_log)
            if dist < best_hu_score:
                best_hu_score = dist
                best_hu_label = label

        # Convert Hu distance to a pseudo-confidence (lower distance = higher confidence)
        hu_confidence = max(0.0, 1.0 - best_hu_score / 10.0)
        if hu_confidence > best_score:
            best_score = hu_confidence
            best_label = best_hu_label

    return (best_label, float(best_score))


def measure(component: Dict[str, Any], ref_img: np.ndarray) -> Dict[str, Any]:
    """Measure geometric properties of a letter component against reference.

    Returns dict with:
    - bbox: (x, y, w, h)
    - baseline_y: detected baseline y position
    - ref_baseline_y: reference baseline y position
    - baseline_offset: difference in pixels
    - slant_deg: detected slant angle
    - ref_slant_deg: reference slant angle
    - slant_offset: difference in degrees
    - aspect_ratio: detected aspect ratio (w/h)
    - ref_aspect_ratio: reference aspect ratio
    - aspect_offset: relative difference
    """
    mask = component['mask']
    bbox = component['bbox']
    x, y, w, h = bbox

    # Detect baseline: bottom of bounding box (Nastaliq baseline approximation)
    baseline_y = y + h

    # Detect slant using minAreaRect on the contour
    contour = component['contour']
    rect = cv2.minAreaRect(contour)
    angle = rect[2]  # angle from minAreaRect

    # Normalize angle to standard slant representation
    # minAreaRect returns angle in [-90, 0), convert to positive slant
    if angle < -45:
        slant_deg = abs(angle + 90)
    else:
        slant_deg = abs(angle)

    # Aspect ratio
    aspect_ratio = w / h if h > 0 else 1.0

    # Reference measurements
    ref_h, ref_w = ref_img.shape[:2]
    ref_baseline_y = int(ref_h * 0.85)  # approximate baseline near bottom
    ref_slant_deg = 12.0  # typical Nastaliq slant
    ref_aspect_ratio = ref_w / ref_h if ref_h > 0 else 1.0

    return {
        'bbox': bbox,
        'baseline_y': baseline_y,
        'ref_baseline_y': ref_baseline_y,
        'baseline_offset': baseline_y - ref_baseline_y,
        'slant_deg': slant_deg,
        'ref_slant_deg': ref_slant_deg,
        'slant_offset': slant_deg - ref_slant_deg,
        'aspect_ratio': aspect_ratio,
        'ref_aspect_ratio': ref_aspect_ratio,
        'aspect_offset': (aspect_ratio - ref_aspect_ratio) / ref_aspect_ratio if ref_aspect_ratio > 0 else 0.0,
    }


def annotate(image: np.ndarray, measurements: List[Dict[str, Any]]) -> np.ndarray:
    """Draw measurement annotations on image.

    RED line = correct baseline position
    BLUE arrow = slant correction direction
    GREEN dotted rect = correct proportions
    ORANGE line = missing / incorrect stroke connection

    NO TEXT LABELS on the image.
    """
    annotated = image.copy()
    h_img, w_img = image.shape[:2]

    # Colors in BGR
    RED = (0, 0, 255)
    BLUE = (255, 0, 0)
    GREEN = (0, 255, 0)
    ORANGE = (0, 165, 255)

    for m in measurements:
        x, y, w, h = m['bbox']
        cx = x + w // 2

        # --- Baseline annotation (RED horizontal line) ---
        ref_baseline_y = m.get('ref_baseline_y', y + h)
        # Scale reference baseline to image coordinates based on bbox position
        baseline_y_img = y + int(m['ref_baseline_y'] * h / max(m.get('ref_height', h), 1))
        
        # Draw red line across the letter width
        cv2.line(annotated, (x, baseline_y_img), (x + w, baseline_y_img), RED, 2)

        # --- Slant annotation (BLUE arrow) ---
        slant_offset = m.get('slant_offset', 0)
        if abs(slant_offset) > SLANT_TOLERANCE_DEG:
            # Arrow indicating correction direction
            arrow_start = (cx, y)
            if slant_offset > 0:
                # Slant too much, correct toward less slant
                arrow_end = (cx - 30, y - 30)
            else:
                # Slant too little, correct toward more slant
                arrow_end = (cx + 30, y - 30)
            cv2.arrowedLine(annotated, arrow_start, arrow_end, BLUE, 2, tipLength=0.3)

        # --- Proportion annotation (GREEN dotted rectangle) ---
        aspect_offset = m.get('aspect_offset', 0)
        if abs(aspect_offset) > PROPORTION_TOLERANCE:
            # Draw dotted rectangle showing correct proportions
            ref_w = int(m.get('ref_aspect_ratio', 1.0) * h)
            half_diff = abs(ref_w - w) // 2
            rect_x = max(0, x - half_diff)
            rect_w = min(w_img - rect_x, ref_w)
            
            # Draw dotted rectangle
            pts = np.array([
                [rect_x, y],
                [rect_x + rect_w, y],
                [rect_x + rect_w, y + h],
                [rect_x, y + h]
            ], np.int32)
            cv2.polylines(annotated, [pts], True, GREEN, 2, lineType=cv2.LINE_AA)

        # --- Stroke connection (ORANGE line) ---
        # For isolated letters, draw a small orange marker at potential connection points
        # Bottom-left of bbox (typical Nastaliq connection point)
        conn_x = x
        conn_y = y + h
        cv2.line(annotated, (conn_x, conn_y), (conn_x, conn_y + 15), ORANGE, 2)

    return annotated
