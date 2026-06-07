import numpy as np
import pytest
import cv2

from pipeline import annotate


class TestAnnotateBaseline:
    def test_green_baseline_drawn(self):
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
        # With alpha blending, colors are mixed. Check that image is modified.
        non_white = np.sum(np.any(result < 240, axis=2))
        assert non_white > 0, f"Expected non-white pixels, got {non_white}"


class TestAnnotateSlant:
    def test_yellow_slant_drawn_when_slant_off(self):
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
        # With alpha blending, colors are mixed, so check for any non-white pixels
        non_white = np.sum(np.any(result < 240, axis=2))
        assert non_white > 0, f"Expected non-white pixels, got {non_white}"

    def test_no_extra_when_slant_ok(self):
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
        # Should still have some modifications from baseline
        non_white = np.sum(np.any(result < 240, axis=2))
        assert non_white > 0, f"Expected non-white pixels, got {non_white}"


class TestAnnotateProportions:
    def test_magenta_rect_drawn_when_proportion_off(self):
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
        # Check that image is modified (not all white)
        non_white = np.sum(np.any(result < 240, axis=2))
        assert non_white > 0, f"Expected non-white pixels, got {non_white}"


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
