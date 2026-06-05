import io
from pathlib import Path
from typing import Any, Generator

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

# We will import from the project root after app modules exist


@pytest.fixture(scope="session")
def test_image_dir() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_color_image() -> np.ndarray:
    """Return a 800x600 color image with a white background and a black rectangle."""
    img = np.ones((800, 600, 3), dtype=np.uint8) * 255
    cv2.rectangle(img, (200, 200), (400, 500), (0, 0, 0), -1)
    return img


@pytest.fixture
def sample_grayscale_image() -> np.ndarray:
    """Return a 800x600 grayscale image with a white background and a black rectangle."""
    img = np.ones((800, 600), dtype=np.uint8) * 255
    cv2.rectangle(img, (200, 200), (400, 500), 0, -1)
    return img


@pytest.fixture
def sample_blurry_image() -> np.ndarray:
    """Return a very blurry image that should fail the quality gate."""
    img = np.ones((800, 600, 3), dtype=np.uint8) * 255
    cv2.rectangle(img, (200, 200), (400, 500), (50, 50, 50), -1)
    img = cv2.GaussianBlur(img, (51, 51), 30)
    return img


@pytest.fixture
def sample_dark_image() -> np.ndarray:
    """Return a very dark image that should fail the quality gate."""
    img = np.ones((800, 600, 3), dtype=np.uint8) * 20
    return img


@pytest.fixture
def sample_small_image() -> np.ndarray:
    """Return a very small image that should fail the quality gate."""
    return np.ones((100, 100, 3), dtype=np.uint8) * 255


@pytest.fixture
def sample_empty_image() -> np.ndarray:
    """Return a completely blank white image."""
    return np.ones((800, 600, 3), dtype=np.uint8) * 255


@pytest.fixture
def sample_letter_blob() -> np.ndarray:
    """Return a grayscale image with a single blob resembling a letter."""
    img = np.ones((400, 400), dtype=np.uint8) * 255
    # Draw a shape resembling a letter (ellipse + line)
    cv2.ellipse(img, (200, 200), (80, 120), 20, 0, 360, 0, -1)
    cv2.line(img, (200, 320), (280, 280), 0, 8)
    return img


@pytest.fixture
def sample_letter_color() -> np.ndarray:
    """Return a color image with a single blob resembling a letter on white."""
    img = np.ones((400, 400, 3), dtype=np.uint8) * 255
    cv2.ellipse(img, (200, 200), (80, 120), 20, 0, 360, (0, 0, 0), -1)
    cv2.line(img, (200, 320), (280, 280), (0, 0, 0), 8)
    return img


def image_to_bytes(img: np.ndarray, format: str = "JPEG") -> io.BytesIO:
    """Convert an OpenCV/numpy image to a BytesIO object."""
    if len(img.shape) == 2:
        pil_img = Image.fromarray(img)
    else:
        pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    buf = io.BytesIO()
    pil_img.save(buf, format=format)
    buf.seek(0)
    return buf
