import numpy as np
import pytest
import cv2

from pipeline import preprocess


class TestPreprocessGrayscale:
    def test_color_input_returns_binary(self):
        img = np.ones((400, 400, 3), dtype=np.uint8) * 255
        cv2.ellipse(img, (200, 200), (80, 120), 0, 0, 360, (0, 0, 0), -1)

        result = preprocess(img)
        # Result should be binary (2D array with values 0 or 255)
        assert len(result.shape) == 2
        assert set(np.unique(result)).issubset({0, 255})

    def test_grayscale_input_works(self):
        img = np.ones((400, 400), dtype=np.uint8) * 255
        cv2.ellipse(img, (200, 200), (80, 120), 0, 0, 360, 0, -1)

        result = preprocess(img)
        assert len(result.shape) == 2


class TestPreprocessNoiseReduction:
    def test_noise_reduced(self):
        # Create noisy image
        img = np.ones((400, 400, 3), dtype=np.uint8) * 255
        # Add noise
        noise = np.random.randint(0, 50, img.shape, dtype=np.uint8)
        img = cv2.add(img, noise)
        # Add a clear letter
        cv2.ellipse(img, (200, 200), (80, 120), 0, 0, 360, (0, 0, 0), -1)

        result = preprocess(img)
        # Should still detect the letter after denoising
        white_pixels = np.sum(result == 255)
        black_pixels = np.sum(result == 0)
        # Both should exist after thresholding
        assert black_pixels > 0
        assert white_pixels > 0


class TestPreprocessOtsuThresholding:
    def test_otsu_separates_foreground(self):
        # White background, black letter
        img = np.ones((400, 400, 3), dtype=np.uint8) * 255
        cv2.ellipse(img, (200, 200), (80, 120), 0, 0, 360, (0, 0, 0), -1)

        result = preprocess(img)
        # After thresholding (inverse), letter should be white (255), background black (0)
        # Since it's inverted: text becomes white
        center_pixel = result[200, 200]
        corner_pixel = result[50, 50]
        assert center_pixel == 255  # letter
        assert corner_pixel == 0    # background
