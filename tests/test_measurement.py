import numpy as np
import pytest
import cv2

from pipeline import measure


class TestMeasureBaseline:
    def test_baseline_at_bottom_of_bbox(self):
        mask = np.zeros((200, 200), dtype=np.uint8)
        cv2.ellipse(mask, (100, 100), (80, 100), 0, 0, 360, 255, -1)

        component = {
            'mask': mask,
            'bbox': (0, 0, 200, 200),
            'contour': cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0][0]
        }

        ref_img = np.ones((128, 128), dtype=np.uint8) * 255
        cv2.ellipse(ref_img, (64, 64), (40, 50), 0, 0, 360, 0, -1)

        result = measure(component, ref_img)
        assert result['baseline_y'] == 200  # bottom of bbox
        assert 'ref_baseline_y' in result
        assert 'baseline_offset' in result


class TestMeasureSlant:
    def test_slant_measurement(self):
        # Create a slanted shape
        mask = np.zeros((200, 200), dtype=np.uint8)
        pts = np.array([[50, 50], [150, 80], [140, 150], [40, 120]])
        cv2.fillPoly(mask, [pts], 255)

        component = {
            'mask': mask,
            'bbox': (40, 50, 110, 100),
            'contour': cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0][0]
        }

        ref_img = np.ones((128, 128), dtype=np.uint8) * 255
        cv2.ellipse(ref_img, (64, 64), (40, 50), 0, 0, 360, 0, -1)

        result = measure(component, ref_img)
        assert 'slant_deg' in result
        assert 'ref_slant_deg' in result
        assert 'slant_offset' in result
        assert result['slant_deg'] >= 0


class TestMeasureProportions:
    def test_aspect_ratio(self):
        # Wide shape
        mask = np.zeros((200, 300), dtype=np.uint8)
        cv2.rectangle(mask, (50, 50), (250, 150), 255, -1)

        component = {
            'mask': mask,
            'bbox': (50, 50, 200, 100),
            'contour': cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0][0]
        }

        ref_img = np.ones((128, 128), dtype=np.uint8) * 255
        cv2.ellipse(ref_img, (64, 64), (40, 50), 0, 0, 360, 0, -1)

        result = measure(component, ref_img)
        assert 'aspect_ratio' in result
        assert 'ref_aspect_ratio' in result
        assert 'aspect_offset' in result
        assert result['aspect_ratio'] == 2.0  # 200/100
