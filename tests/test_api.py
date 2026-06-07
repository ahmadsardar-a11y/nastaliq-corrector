import io
import pytest
from fastapi.testclient import TestClient
from PIL import Image
import numpy as np
import cv2

from conftest import image_to_bytes


@pytest.fixture
def client() -> TestClient:
    from main import app
    return TestClient(app)


class TestHealthCheck:
    def test_health_check_returns_ok(self, client: TestClient):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "nastaliq-corrector"


class TestUploadValidImage:
    def test_upload_jpeg_returns_image(self, client: TestClient):
        # Create a simple test image
        img = np.ones((800, 600, 3), dtype=np.uint8) * 255
        # Draw a black blob resembling a letter
        cv2.ellipse(img, (300, 400), (80, 120), 0, 0, 360, (0, 0, 0), -1)
        img_bytes = image_to_bytes(img, "JPEG")

        response = client.post(
            "/upload-simple",
            files={"file": ("test_letter.jpg", img_bytes, "image/jpeg")}
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
        # Verify it's a valid image
        result_img = Image.open(io.BytesIO(response.content))
        assert result_img.size == (600, 800)

    def test_upload_png_returns_image(self, client: TestClient):
        img = np.ones((800, 600, 3), dtype=np.uint8) * 255
        cv2.ellipse(img, (300, 400), (80, 120), 0, 0, 360, (0, 0, 0), -1)
        img_bytes = image_to_bytes(img, "PNG")

        response = client.post(
            "/upload-simple",
            files={"file": ("test_letter.png", img_bytes, "image/png")}
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"


class TestUploadInvalidFormat:
    def test_upload_gif_rejected(self, client: TestClient):
        # Create a simple GIF-like bytes
        gif_bytes = io.BytesIO(b"GIF89a\x01\x00\x01\x00\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;")
        response = client.post(
            "/upload-simple",
            files={"file": ("test.gif", gif_bytes, "image/gif")}
        )
        assert response.status_code == 400
        data = response.json()
        assert "Only JPEG and PNG" in data["detail"]

    def test_upload_bmp_rejected(self, client: TestClient):
        # Create a simple BMP-like bytes
        bmp_bytes = io.BytesIO(b"BM" + b"\x00" * 100)
        response = client.post(
            "/upload-simple",
            files={"file": ("test.bmp", bmp_bytes, "image/bmp")}
        )
        assert response.status_code == 400


class TestUploadOversizedImage:
    def test_upload_large_image_rejected(self, client: TestClient):
        # Create a large image (~15MB of raw data) with noise so it compresses large
        img = np.random.randint(0, 256, (4000, 3000, 3), dtype=np.uint8)
        large_bytes = io.BytesIO()
        pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        pil_img.save(large_bytes, "JPEG", quality=95)
        large_bytes.seek(0)

        response = client.post(
            "/upload-simple",
            files={"file": ("large.jpg", large_bytes, "image/jpeg")}
        )
        assert response.status_code == 400
        data = response.json()
        assert "too large" in data["detail"].lower()


class TestUploadEmptyRequest:
    def test_empty_request_rejected(self, client: TestClient):
        response = client.post("/upload-simple")
        assert response.status_code == 422


class TestUploadNoLetters:
    def test_blank_image_no_crash(self, client: TestClient):
        # Blank white image
        img = np.ones((800, 600, 3), dtype=np.uint8) * 255
        img_bytes = image_to_bytes(img, "JPEG")

        response = client.post(
            "/upload-simple",
            files={"file": ("blank.jpg", img_bytes, "image/jpeg")}
        )
        # Should return 200 with a "No letters detected" annotated image
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
