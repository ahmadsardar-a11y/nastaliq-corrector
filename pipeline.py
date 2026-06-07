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
    # Distance transform to find thick parts (letters) vs thin parts (lines)
    dist = cv2.distanceTransform(binary, cv2.DIST_L2, 5)
    
    # Threshold to keep only thick parts (letters)
    _, thick_parts = cv2.threshold(dist, 5, 255, cv2.THRESH_BINARY)
    thick_parts = thick_parts.astype(np.uint8)
    
    # Find connected components on thick parts
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(thick_parts, connectivity=8)
    
    h_total, w_total = thick_parts.shape
    max_area = MAX_COMPONENT_AREA * h_total * w_total
    
    components = []
    for i in range(1, num_labels):  # skip background (0)
        x, y, w, h, area = stats[i]
        
        # Filter by size
        if area < MIN_COMPONENT_AREA or area > max_area:
            continue
        
        # Filter out obvious lines
        is_long_horizontal = w > h * 8 and h < 10
        is_long_vertical = h > w * 8 and w < 10
        if is_long_horizontal or is_long_vertical:
            continue
        
        # Extract mask from the thick parts
        mask = np.zeros_like(binary)
        mask[labels == i] = 255
        
        # Dilate the mask to include the original letter shape
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.dilate(mask, kernel, iterations=2)
        
        # Find contour
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            continue
        
        contour = max(contours, key=cv2.contourArea)
        
        # Recalculate bounding box
        x, y, w, h = cv2.boundingRect(contour)
        
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


def annotate(image: np.ndarray, measurements: List[Dict[str, Any]], references: Dict[str, np.ndarray] = None) -> np.ndarray:
    """Draw ideal letter overlay on user's writing for direct visual comparison."""
    annotated = image.copy()
    h_img, w_img = image.shape[:2]

    CYAN = (255, 255, 0)
    MAGENTA = (255, 0, 255)
    GREEN = (0, 255, 0)
    WHITE = (255, 255, 255)

    for m in measurements:
        x, y, w, h = m['bbox']
        label = m.get('label', '')
        confidence = m.get('confidence', 0)

        # Skip if confidence is too low (likely not a real letter)
        if confidence < 0.3:
            continue

        # --- Draw ideal letter overlay ---
        if references and label in references:
            ref_img = references[label]
            ref_h, ref_w = ref_img.shape[:2]

            # Resize reference to match user's letter size
            scale = min(w / ref_w, h / ref_h) if ref_w > 0 and ref_h > 0 else 1.0
            new_w = int(ref_w * scale)
            new_h = int(ref_h * scale)

            if new_w > 0 and new_h > 0:
                # Resize reference image
                ref_resized = cv2.resize(ref_img, (new_w, new_h))

                # Calculate position to center the reference over user's letter
                offset_x = x + (w - new_w) // 2
                offset_y = y + (h - new_h) // 2

                # Ensure we stay within image bounds
                x1 = max(0, offset_x)
                y1 = max(0, offset_y)
                x2 = min(w_img, offset_x + new_w)
                y2 = min(h_img, offset_y + new_h)

                # Extract the region from reference that fits
                ref_x1 = max(0, -offset_x)
                ref_y1 = max(0, -offset_y)
                ref_x2 = ref_x1 + (x2 - x1)
                ref_y2 = ref_y1 + (y2 - y1)

                ref_crop = ref_resized[ref_y1:ref_y2, ref_x1:ref_x2]

                if ref_crop.size > 0:
                    # Create colored overlay
                    overlay = annotated.copy()

                    # Convert to BGR if grayscale
                    if len(ref_crop.shape) == 2:
                        ref_color = cv2.cvtColor(ref_crop, cv2.COLOR_GRAY2BGR)
                    else:
                        ref_color = ref_crop

                    # Create mask from reference (black pixels are the letter)
                    ref_gray = cv2.cvtColor(ref_color, cv2.COLOR_BGR2GRAY)
                    _, ref_mask = cv2.threshold(ref_gray, 200, 255, cv2.THRESH_BINARY_INV)

                    # Create cyan colored letter
                    cyan_letter = np.zeros_like(ref_color)
                    cyan_letter[:, :] = CYAN

                    # Only keep cyan where the reference letter is
                    cyan_masked = cv2.bitwise_and(cyan_letter, cyan_letter, mask=ref_mask)

                    # Blend with semi-transparency
                    region = overlay[y1:y2, x1:x2]
                    alpha = 0.5
                    blended = cv2.addWeighted(cyan_masked, alpha, region, 1 - alpha, 0)
                    overlay[y1:y2, x1:x2] = blended

                    # Draw outline around the reference letter
                    ref_contours, _ = cv2.findContours(ref_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    for cnt in ref_contours:
                        cnt_offset = cnt + np.array([[x1, y1]])
                        cv2.drawContours(overlay, [cnt_offset], -1, CYAN, 2)

                    annotated = overlay

                    # Add label
                    cv2.putText(annotated, "ideal", (x1, max(20, y1 - 5)),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, CYAN, 1)

        # --- Baseline guide ---
        baseline_y = y + h - 5
        cv2.line(annotated, (x - 10, baseline_y), (x + w + 10, baseline_y), GREEN, 2)

        # --- Connection point ---
        conn_x = x + w - 5
        conn_y = y + h - 5
        cv2.circle(annotated, (conn_x, conn_y), 4, MAGENTA, -1)

    # Add letter detection info at top
    if measurements:
        label = measurements[0].get('label', 'letter')
        confidence = measurements[0].get('confidence', 0)
        cv2.putText(annotated, f"Detected: {label} ({confidence:.0%})", (20, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, WHITE, 2)
        cv2.putText(annotated, "Cyan = ideal shape", (20, 55),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, CYAN, 2)

    return annotated
