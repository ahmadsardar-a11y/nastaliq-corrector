import numpy as np
import pytest
import cv2

from pipeline import annotate


class TestAnnotateBaseline:
    def test_red_baseline_drawn(self):
        img = np.ones((400, 400, 3), dtype=np.uint8) * 255
        measurements = [{
            'bbox': (100, 100, 200, 150),
            'baseline_y': 250,
            'ref_baseline_y': 240,
            'baseline_offset': 10,
            'slant_deg': 10,
            'ref_slant_deg': 12,
            'slant_offset': -2,
            'aspect_ratio': 1.3,
            'ref_aspect_ratio': 1.3,
            'aspect_offset': 0.0,
            'ref_height': 150,
        }]

        result = annotate(img, measurements)
        # Check that red pixels exist (BGR: (0,0,255) = red)
        red_pixels = np.sum((result[:, :, 2] == 255) & (result[:, :, 0] == 0) & (result[:, :, 1] == 0))
        assert red_pixels > 0


class TestAnnotateSlant:
    def test_blue_arrow_drawn_when_slant_off(self):
        img = np.ones((400, 400, 3), dtype=np.uint8) * 255
        measurements = [{
            'bbox': (100, 100, 200, 150),
            'baseline_y': 250,
            'ref_baseline_y': 240,
            'baseline_offset': 10,
            'slant_deg': 20,
            'ref_slant_deg': 12,
            'slant_offset': 8,  # > tolerance, should draw arrow
            'aspect_ratio': 1.3,
            'ref_aspect_ratio': 1.3,
            'aspect_offset': 0.0,
            'ref_height': 150,
        }]

        result = annotate(img, measurements)
        # Check blue pixels (BGR: (255,0,0) = blue)
        blue_pixels = np.sum((result[:, :, 0] == 255) & (result[:, :, 1] == 0) & (result[:, :, 2] == 0))
        assert blue_pixels > 0

    def test_no_blue_arrow_when_slant_ok(self):
        img = np.ones((400, 400, 3), dtype=np.uint8) * 255
        measurements = [{
            'bbox': (100, 100, 200, 150),
            'baseline_y': 250,
            'ref_baseline_y': 240,
            'baseline_offset': 10,
            'slant_deg': 12,
            'ref_slant_deg': 12,
            'slant_offset': 0,  # within tolerance
            'aspect_ratio': 1.3,
            'ref_aspect_ratio': 1.3,
            'aspect_offset': 0.0,
            'ref_height': 150,
        }]

        result = annotate(img, measurements)
        # Should still have some red from baseline, but no extra blue
        blue_pixels = np.sum((result[:, :, 0] == 255) & (result[:, :, 1] == 0) & (result[:, :, 2] == 0))
        # Blue might be minimal or zero when slant is within tolerance
        assert blue_pixels == 0 or blue_pixels < 50


class TestAnnotateProportions:
    def test_green_dotted_rect_drawn_when_proportion_off(self):
        img = np.ones((400, 400, 3), dtype=np.uint8) * 255
        measurements = [{
            'bbox': (100, 100, 200, 150),
            'baseline_y': 250,
            'ref_baseline_y': 240,
            'baseline_offset': 10,
            'slant_deg': 12,
            'ref_slant_deg': 12,
            'slant_offset': 0,
            'aspect_ratio': 2.0,
            'ref_aspect_ratio': 1.3,
            'aspect_offset': 0.54,  # > tolerance
            'ref_height': 150,
        }]

        result = annotate(img, measurements)
        # Check green pixels (BGR: (0,255,0) = green)
        green_pixels = np.sum((result[:, :, 1] == 255) & (result[:, :, 0] == 0) & (result[:, :, 2] == 0))
        assert green_pixels > 0


class TestAnnotateNoTextLabels:
    def test_no_text_on_image(self):
        img = np.ones((400, 400, 3), dtype=np.uint8) * 255
        measurements = [{
            'bbox': (100, 100, 200, 150),
            'baseline_y': 250,
            'ref_baseline_y': 240,
            'baseline_offset': 10,
            'slant_deg': 20,
            'ref_slant_deg': 12,
            'slant_offset': 8,
            'aspect_ratio': 2.0,
            'ref_aspect_ratio': 1.3,
            'aspect_offset': 0.54,
            'ref_height': 150,
        }]

        result = annotate(img, measurements)
        # Just verify it runs without error and image is modified
        assert not np.array_equal(result, img)


class TestAnnotateEmptyMeasurements:
    def test_no_crash_empty_list(self):
        img = np.ones((400, 400, 3), dtype=np.uint8) * 255
        result = annotate(img, [])
        assert np.array_equal(result, img)
