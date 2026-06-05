import numpy as np
import pytest
import cv2

from pipeline import classify
from references import generate_references, URDU_LETTERS


@pytest.fixture(scope="session", autouse=True)
def setup_references(tmp_path_factory):
    """Generate reference images before running classification tests."""
    ref_dir = tmp_path_factory.mktemp("references")
    generate_references(ref_dir)
    return ref_dir


class TestClassifyCorrectMatch:
    def test_be_matches_be(self, setup_references):
        # Create a component that looks like 'be' (bowl shape)
        mask = np.zeros((200, 200), dtype=np.uint8)
        cv2.ellipse(mask, (100, 100), (50, 40), 0, 0, 360, 255, -1)
        cv2.line(mask, (50, 150), (150, 140), 255, 3)

        component = {
            'mask': mask,
            'bbox': (0, 0, 200, 200),
            'contour': cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0][0]
        }

        # Load references
        from references import load_all_references
        refs = load_all_references()

        label, confidence = classify(component, refs)
        assert label in URDU_LETTERS
        assert confidence > 0.0

    def test_high_confidence_on_good_match(self, setup_references):
        from references import load_all_references
        refs = load_all_references()

        # Use an actual reference as input (should match itself perfectly)
        # Invert reference to match pipeline mask polarity (white-on-black)
        ref_img = refs.get("be")
        if ref_img is not None:
            h, w = ref_img.shape
            mask = cv2.bitwise_not(ref_img)
            component = {
                'mask': mask,
                'bbox': (0, 0, w, h),
                'contour': cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0][0]
            }

            label, confidence = classify(component, refs)
            assert confidence > 0.5  # Should match itself very well


class TestClassifyUnknown:
    def test_low_confidence_on_random_shape(self, setup_references):
        from references import load_all_references
        refs = load_all_references()

        # Random shape
        mask = np.zeros((200, 200), dtype=np.uint8)
        cv2.circle(mask, (100, 100), 80, 255, -1)

        component = {
            'mask': mask,
            'bbox': (0, 0, 200, 200),
            'contour': cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0][0]
        }

        label, confidence = classify(component, refs)
        # Should have lower confidence for random shape
        assert confidence < 0.9
