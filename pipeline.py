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
    # Skip for nearly-uniform images (lap_var near 0) - these are blank/synthetic,
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

    # Gaussian blur for noise reduction — use smaller kernel to preserve thin strokes
    # Nastaliq has thin tails (e.g., ب) that blur can destroy
    blurred = cv2.GaussianBlur(gray, (1, 1), 0)

    # Otsu thresholding (inverse so text is white on black)
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Morphological closing to reconnect thin strokes that got separated
    # This helps letters like ب (bowl + tail) stay as one component
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)

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

        # Filter out long thin lines (practice lines, not letters)
        # A line is very long in one dimension and very short in the other
        is_long_horizontal = w > h * 12 and h < 6  # Very wide but very short = practice line
        is_long_vertical = h > w * 12 and w < 6    # Very tall but very narrow = practice line
        if is_long_horizontal or is_long_vertical:
            continue  # Definitely a practice line

        # Also filter by filling ratio - but be more lenient for curved Nastaliq strokes
        # which can be elongated but still have moderate fill ratio
        bbox_area = w * h
        fill_ratio = area / bbox_area if bbox_area > 0 else 0
        if fill_ratio < 0.08 and (w > h * 5 or h > w * 5):
            # Very sparse component - likely a line or artifact
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

    # Merge nearby components that are likely parts of the same Nastaliq letter
    # (e.g., thick bowl + thin tail of ب that got separated during thresholding)
    MERGE_DISTANCE = 20  # pixels
    merged = []
    used = set()

    for i, comp_a in enumerate(components):
        if i in used:
            continue
        x1, y1, w1, h1 = comp_a['bbox']
        cx1, cy1 = x1 + w1//2, y1 + h1//2

        # Start with this component's mask
        merged_mask = comp_a['mask'].copy()
        merged_bbox = [x1, y1, w1, h1]
        merged_area = comp_a['area']

        for j, comp_b in enumerate(components):
            if j == i or j in used:
                continue
            x2, y2, w2, h2 = comp_b['bbox']
            cx2, cy2 = x2 + w2//2, y2 + h2//2

            # Check distance between centers
            dist = np.sqrt((cx1 - cx2)**2 + (cy1 - cy2)**2)
            if dist < MERGE_DISTANCE:
                # Merge masks
                merged_mask = cv2.bitwise_or(merged_mask, comp_b['mask'])
                # Expand bounding box
                merged_bbox[0] = min(merged_bbox[0], x2)
                merged_bbox[1] = min(merged_bbox[1], y2)
                merged_bbox[2] = max(merged_bbox[0] + merged_bbox[2], x2 + w2) - merged_bbox[0]
                merged_bbox[3] = max(merged_bbox[1] + merged_bbox[3], y2 + h2) - merged_bbox[1]
                merged_area += comp_b['area']
                used.add(j)

        used.add(i)

        # Recalculate contour from merged mask
        merged_bbox = tuple(merged_bbox)
        contours, _ = cv2.findContours(merged_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            merged_contour = max(contours, key=cv2.contourArea)
            merged.append({
                'mask': merged_mask,
                'bbox': merged_bbox,
                'contour': merged_contour,
                'area': merged_area
            })

    return merged


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
        # Resize reference to match crop dimensions (same scale)
        ref_resized = cv2.resize(ref_img, (w, h))
        # Invert reference to match mask polarity (mask is white-on-black)
        ref_inverted = cv2.bitwise_not(ref_resized)

        # Direct pixel comparison since sizes match exactly
        diff = cv2.absdiff(crop.astype(np.float32), ref_inverted.astype(np.float32))
        score = 1.0 - (np.mean(diff) / 255.0)

        if score > best_score:
            best_score = score
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


def annotate(image: np.ndarray, measurements: List[Dict[str, Any]], references: Dict[str, np.ndarray] = None) -> np.ndarray:
    """Draw bold ideal letter outline for clear visual comparison."""
    annotated = image.copy()
    h_img, w_img = image.shape[:2]

    CYAN = (255, 255, 0)     # Ideal outline
    GREEN = (0, 255, 0)      # Baseline
    MAGENTA = (255, 0, 255)  # Connection
    WHITE = (255, 255, 255)

    if not measurements:
        return annotated

    # Only annotate the largest component (ignore tiny fragments/dots)
    measurements = sorted(measurements, key=lambda m: m.get('area', 0), reverse=True)
    m = measurements[0]

    x, y, w, h = m['bbox']
    label = m.get('label', '')
    confidence = m.get('confidence', 0)

    # --- Draw ideal letter as bold outline ---
    if references and label in references:
        ref_img = references[label]
        ref_h, ref_w = ref_img.shape[:2]

        if ref_w > 0 and ref_h > 0:
            # Resize reference to match user's letter bbox (stretch to fit)
            new_w = max(1, w)
            new_h = max(1, h)

            ref_resized = cv2.resize(ref_img, (new_w, new_h))

            # Place directly over user's letter bbox (no centering offset)
            x1 = max(0, x)
            y1 = max(0, y)
            x2 = min(w_img, x + new_w)
            y2 = min(h_img, y + new_h)

            # Map back to reference coords
            rx1 = 0
            ry1 = 0
            rx2 = rx1 + (x2 - x1)
            ry2 = ry1 + (y2 - y1)

            ref_crop = ref_resized[ry1:ry2, rx1:rx2]

            if ref_crop.size > 0:
                # Threshold to get letter mask from reference
                if len(ref_crop.shape) == 3:
                    ref_gray = cv2.cvtColor(ref_crop, cv2.COLOR_BGR2GRAY)
                else:
                    ref_gray = ref_crop

                _, ref_mask = cv2.threshold(ref_gray, 200, 255, cv2.THRESH_BINARY_INV)

                # Find outer contour of ideal letter
                ref_contours, _ = cv2.findContours(ref_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                # Shift contours to image position
                for cnt in ref_contours:
                    cnt_shifted = cnt + np.array([[x1, y1]])
                    # Thick bold outline
                    cv2.drawContours(annotated, [cnt_shifted], -1, CYAN, 4)

    # --- Baseline marker (green) ---
    baseline_y = y + h - 5
    cv2.line(annotated, (x, baseline_y), (x + w, baseline_y), GREEN, 2)

    # --- Connection point (magenta) ---
    conn_x = x + w - 5
    conn_y = y + h - 5
    cv2.circle(annotated, (conn_x, conn_y), 4, MAGENTA, -1)

    # --- Confidence label (top-left of bbox) ---
    label_text = f"{label} ({confidence:.0%})" if label else "?"
    cv2.putText(annotated, label_text, (x, max(20, y - 5)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, WHITE, 2)

    return annotated
