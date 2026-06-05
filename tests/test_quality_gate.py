import numpy as np
import pytest
import cv2

from pipeline import quality_gate


class TestQualityGateGoodPhoto:
    def test_well_lit_photo_passes(self):
        # Create a well-lit image
        img = np.ones((800, 600, 3), dtype=np.uint8) * 200
        passed, msg = quality_gate(img)
        assert passed is True
        assert msg == ""

    def test_high_res_photo_passes(self):
        img = np.ones((2000, 1500, 3), dtype=np.uint8) * 180
        passed, msg = quality_gate(img)
        assert passed is True


class TestQualityGateSlightlyDark:
    def test_slightly_dark_photo_passes(self):
        # Underexposed but readable (mean brightness ~60)
        img = np.ones((800, 600, 3), dtype=np.uint8) * 60
        passed, msg = quality_gate(img)
        # Should pass (forgiving) — our threshold is <20 for rejection
        assert passed is True


class TestQualityGateVeryBlurry:
    def test_severe_blur_rejected(self):
        # Create a realistic image with structure, then blur it
        img = np.ones((800, 600, 3), dtype=np.uint8) * 200
        # Add structure so blurring actually reduces edge variance
        cv2.line(img, (100, 100), (500, 500), (50, 50, 50), 5)
        cv2.circle(img, (300, 300), 100, (100, 100, 100), 3)
        img = cv2.GaussianBlur(img, (51, 51), 30)
        passed, msg = quality_gate(img)
        assert passed is False
        assert "blurry" in msg.lower()


class TestQualityGateTooSmall:
    def test_tiny_image_rejected(self):
        img = np.ones((150, 150, 3), dtype=np.uint8) * 200
        passed, msg = quality_gate(img)
        assert passed is False
        assert "resolution" in msg.lower()


class TestQualityGateTooDark:
    def test_pitch_black_rejected(self):
        img = np.ones((800, 600, 3), dtype=np.uint8) * 10
        passed, msg = quality_gate(img)
        assert passed is False
        assert "dark" in msg.lower()


class TestQualityGateEdgeCases:
    def test_exactly_200px_passes(self):
        # 200px is the minimum threshold (QUALITY_MIN_SIZE = 200)
        img = np.ones((200, 200, 3), dtype=np.uint8) * 200
        passed, msg = quality_gate(img)
        assert passed is True

    def test_199px_rejected(self):
        img = np.ones((199, 199, 3), dtype=np.uint8) * 200
        passed, msg = quality_gate(img)
        assert passed is False
