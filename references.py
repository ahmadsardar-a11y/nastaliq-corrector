"""Reference letter data and loading utilities."""

import json
from pathlib import Path
from typing import Dict

import cv2
import numpy as np

REFERENCES_DIR = Path(__file__).parent / "references"

# 33 isolated Urdu letters (basic disconnected forms)
URDU_LETTERS = [
    "alef",       # ا
    "be",         # ب
    "pe",         # پ
    "te",         # ت
    "the",        # ث
    "jeem",       # ج
    "che",        # چ
    "he",         # ح
    "khe",        # خ
    "dal",        # د
    "ddal",       # ڈ
    "zal",        # ذ
    "re",         # ر
    "ze",         # ز
    "zhe",        # ژ
    "seen",       # س
    "sheen",      # ش
    "sad",        # ص
    "zad",        # ض
    "tah",        # ط
    "zah",        # ظ
    "ain",        # ع
    "ghain",      # غ
    "fe",         # ف
    "qaf",        # ق
    "kaf",        # ک
    "gaf",        # گ
    "lam",        # ل
    "meem",       # م
    "noon",       # ن
    "waw",        # و
    "heh",        # ہ
    "yeh",        # ی
    "hamza",      # ء
]


def generate_references(output_dir: Path = REFERENCES_DIR, size: int = 128) -> None:
    """Generate reference images for all Urdu letters.

    Since we don't have a Nastaliq font installed, we generate simplified
    reference shapes that approximate Nastaliq letter forms. These are
    sufficient for template matching in the MVP.

    In a production system, these would be generated from a proper Nastaliq font
    like Jameel Noori Nastaleeq.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    for letter in URDU_LETTERS:
        # Create a white canvas
        img = np.ones((size, size), dtype=np.uint8) * 255

        # Generate a simplified shape based on letter category
        if letter in ("alef", "dal", "ddal", "re", "ze", "zhe"):
            # Vertical/tall letters — tall thin stroke
            cv2.line(img, (size//2, size//4), (size//2, 3*size//4), 0, 4)
            if letter == "re":
                cv2.line(img, (size//2, 3*size//4), (3*size//4, 7*size//8), 0, 3)

        elif letter in ("be", "pe", "te", "the", "jeem", "che", "he", "khe"):
            # Bowl letters — bowl shape with/without dot
            center = (size//2, size//2)
            axes = (size//4, size//5)
            cv2.ellipse(img, center, axes, 0, 0, 360, 0, -1)
            cv2.ellipse(img, center, axes, 0, 0, 360, 0, 3)
            # Add connection stroke below
            cv2.line(img, (size//4, 3*size//4), (3*size//4, 7*size//8), 0, 3)
            # Dot for pe, te, the, che, khe
            if letter in ("pe", "te", "the", "che", "khe"):
                dot_y = size//4 if letter in ("pe", "te") else size//3
                cv2.circle(img, (3*size//4, dot_y), 4, 0, -1)

        elif letter in ("seen", "sheen", "sad", "zad"):
            # Three-tooth letters
            for i in range(3):
                x = size//4 + i * size//6
                cv2.line(img, (x, size//2), (x, size//4), 0, 3)
            # Sheen has dots above
            if letter == "sheen":
                for i in range(3):
                    x = size//4 + i * size//6
                    cv2.circle(img, (x, size//6), 3, 0, -1)

        elif letter in ("ain", "ghain"):
            # Bowl with gap at top
            center = (size//2, size//2)
            axes = (size//4, size//4)
            cv2.ellipse(img, center, axes, 0, 45, 315, 0, 4)
            # Ghain has dot above
            if letter == "ghain":
                cv2.circle(img, (size//2, size//4), 4, 0, -1)

        elif letter in ("fe", "qaf", "kaf", "gaf"):
            # Tall loop letters
            cv2.line(img, (size//3, size//4), (size//3, 3*size//4), 0, 3)
            cv2.line(img, (size//3, size//4), (2*size//3, size//3), 0, 3)
            # Qaf and gaf have dots
            if letter in ("qaf", "gaf"):
                cv2.circle(img, (2*size//3, size//4), 4, 0, -1)

        elif letter in ("lam", "noon"):
            # Vertical with curve
            cv2.line(img, (size//3, size//4), (size//3, 3*size//4), 0, 4)
            cv2.line(img, (size//3, size//4), (2*size//3, size//3), 0, 3)
            if letter == "noon":
                cv2.circle(img, (2*size//3, size//4), 4, 0, -1)

        elif letter in ("waw"):
            # Circle-ish
            center = (size//2, size//2)
            cv2.circle(img, center, size//5, 0, 4)

        elif letter in ("yeh", "heh"):
            # Two-eyed
            center1 = (size//3, 2*size//3)
            center2 = (2*size//3, 2*size//3)
            cv2.circle(img, center1, size//8, 0, 3)
            cv2.circle(img, center2, size//8, 0, 3)
            # Yeh has dots below
            if letter == "yeh":
                cv2.circle(img, (size//2, 5*size//6), 3, 0, -1)

        elif letter == "hamza":
            # Small shape
            cv2.line(img, (size//3, size//2), (2*size//3, size//2), 0, 3)
            cv2.line(img, (size//2, size//3), (size//2, 2*size//3), 0, 3)

        else:
            # Default: simple diagonal line
            cv2.line(img, (size//4, size//4), (3*size//4, 3*size//4), 0, 4)

        # Save image
        img_path = output_dir / f"{letter}.png"
        cv2.imwrite(str(img_path), img)

        # Save metadata
        meta = {
            "letter": letter,
            "size": size,
            "baseline_y": int(size * 0.85),
            "slant_deg": 12.0,
            "aspect_ratio": 1.0,
        }
        meta_path = output_dir / f"{letter}.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)


def load_reference(letter: str) -> np.ndarray:
    """Load a reference image for a given letter.

    Args:
        letter: The letter identifier (e.g., 'be', 'pe', etc.)

    Returns:
        Grayscale reference image as numpy array.
    """
    img_path = REFERENCES_DIR / f"{letter}.png"
    if not img_path.exists():
        generate_references()
    img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(f"Could not load reference for letter: {letter}")
    return img


def load_all_references() -> Dict[str, np.ndarray]:
    """Load all reference images.

    Returns:
        Dictionary mapping letter names to grayscale reference images.
    """
    references = {}
    for letter in URDU_LETTERS:
        try:
            references[letter] = load_reference(letter)
        except FileNotFoundError:
            continue
    return references


def load_reference_meta(letter: str) -> dict:
    """Load metadata for a reference letter."""
    meta_path = REFERENCES_DIR / f"{letter}.json"
    if not meta_path.exists():
        generate_references()
    with open(meta_path, "r", encoding="utf-8") as f:
        return json.load(f)
