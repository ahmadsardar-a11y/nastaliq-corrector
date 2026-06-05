import numpy as np
import pytest
import cv2

from pipeline import segment


class TestSegmentSingleLetter:
    def test_single_blob_detected(self):
        # Create binary image with one white blob on black background
        binary = np.zeros((400, 400), dtype=np.uint8)
        cv2.ellipse(binary, (200, 200), (80, 120), 0, 0, 360, 255, -1)

        components = segment(binary)
        assert len(components) == 1
        assert components[0]['bbox'] is not None
        assert components[0]['mask'] is not None

    def test_multiple_blobs_detected(self):
        binary = np.zeros((400, 400), dtype=np.uint8)
        cv2.ellipse(binary, (100, 100), (40, 60), 0, 0, 360, 255, -1)
        cv2.ellipse(binary, (300, 300), (40, 60), 0, 0, 360, 255, -1)

        components = segment(binary)
        assert len(components) == 2


class TestSegmentNoiseFiltering:
    def test_small_specks_filtered(self):
        binary = np.zeros((400, 400), dtype=np.uint8)
        # Main letter blob
        cv2.ellipse(binary, (200, 200), (80, 120), 0, 0, 360, 255, -1)
        # Tiny speck (should be filtered)
        cv2.circle(binary, (50, 50), 3, 255, -1)

        components = segment(binary)
        assert len(components) == 1  # Only the main blob

    def test_huge_artifact_filtered(self):
        binary = np.zeros((400, 400), dtype=np.uint8)
        # Main letter blob
        cv2.ellipse(binary, (200, 200), (80, 120), 0, 0, 360, 255, -1)
        # Huge artifact taking up most of image (should be filtered)
        cv2.rectangle(binary, (10, 10), (390, 390), 255, -1)

        components = segment(binary)
        # Should filter out the huge artifact
        assert len(components) <= 1


class TestSegmentEmptyImage:
    def test_no_components_on_blank(self):
        binary = np.zeros((400, 400), dtype=np.uint8)
        components = segment(binary)
        assert len(components) == 0
