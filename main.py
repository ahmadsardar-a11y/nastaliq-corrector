"""FastAPI application for Nastaliq calligraphy correction."""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import Response, FileResponse
from fastapi.staticfiles import StaticFiles
import numpy as np
import cv2
from PIL import Image
import io
from pathlib import Path

from pipeline import quality_gate, preprocess, segment, classify, measure, annotate
from references import load_all_references

app = FastAPI(title="Nastaliq Corrector")

# Load reference images on startup
_ref_cache = None


def get_references():
    global _ref_cache
    if _ref_cache is None:
        _ref_cache = load_all_references()
    return _ref_cache


# Serve static files (frontend) — mount at /static, serve index.html at root
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/")
    def serve_index():
        return FileResponse(static_dir / "index.html")

    @app.get("/health")
    def health_check():
        return {"status": "ok", "service": "nastaliq-corrector"}


@app.post("/upload-simple")
async def upload_simple(file: UploadFile = File(...)):
    # Validate content type
    if file.content_type not in ("image/jpeg", "image/png", "image/jpg"):
        raise HTTPException(
            status_code=400,
            detail="Only JPEG and PNG images are supported."
        )

    # Read image bytes
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="Image too large. Max size: 10MB."
        )

    # Convert to OpenCV image
    try:
        pil_img = Image.open(io.BytesIO(contents))
        # Convert to RGB if needed
        if pil_img.mode != "RGB":
            pil_img = pil_img.convert("RGB")
        image = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Could not read image: {str(e)}"
        )

    # Quality gate
    passed, message = quality_gate(image)
    if not passed:
        raise HTTPException(status_code=400, detail=message)

    # Preprocess
    processed = preprocess(image)

    # Segment
    components = segment(processed)
    if not components:
        # Return original with a note — no letters detected
        annotated = image.copy()
        cv2.putText(
            annotated,
            "No letters detected",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 0, 255),
            2
        )
        _, buf = cv2.imencode(".png", annotated)
        return Response(content=buf.tobytes(), media_type="image/png")

    # Load references
    references = get_references()

    # Classify, measure, and collect annotations
    measurements = []
    for component in components:
        label, confidence = classify(component, references)
        if confidence < 0.3 or label not in references:
            continue
        ref_img = references[label]
        measurement = measure(component, ref_img)
        measurement["label"] = label
        measurement["confidence"] = confidence
        measurements.append(measurement)

    # Annotate
    annotated = annotate(image, measurements)

    # Return as PNG
    _, buf = cv2.imencode(".png", annotated)
    return Response(content=buf.tobytes(), media_type="image/png")
