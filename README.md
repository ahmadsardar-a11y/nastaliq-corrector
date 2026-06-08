# Nastaliq Corrector — Status: ABANDONED

**Status:** Closed / Archived  
**Date:** 2026-06-08  
**Reason:** Classical CV pipeline insufficient for Nastaliq calligraphy stroke segmentation. Multiple preprocessing and segmentation iterations failed to reliably capture thin-to-thick stroke transitions and faint ink on paper. ML-based approach (CNN/Transformer) would be required for production-quality results — deferred to future exploration.

**Final commit:** d65319c  
**Archive tag:** v1.0-abandoned  
**Live URL:** https://nastaliq-corrector.onrender.com (to be shut down)

## Project History

- **2026-06-03:** Design agent created specs, architecture, MVP scope
- **2026-06-05:** Coding agent implemented classical CV pipeline (quality gate → preprocess → segment → classify → measure → annotate)
- **2026-06-05:** QA passed 37/37 tests
- **2026-06-07:** Deployment to Render, initial testing with practice images
- **2026-06-08:** Iteration 1 — reduced blur, morphological closing, fixed classification
- **2026-06-08:** Iteration 2 — larger kernel, component merging, relaxed filters
- **2026-06-08:** Final test — still failed to segment faint strokes reliably. Project abandoned.

## Lessons Learned

1. **Classical CV (thresholding + connected components) is inadequate for Nastaliq.** The script's thin-to-thick strokes, faint ink, and curved bowls break standard document-scanning pipelines.
2. **Morphological operations help but don't solve the fundamental problem.** A 7x7 or 9x9 kernel might bridge gaps, but it also distorts the letter shape.
3. **Adaptive thresholding + contrast enhancement might help, but the real solution is ML.** A CNN or transformer trained on Nastaliq stroke data would handle variation in ink density, stroke width, and style.
4. **Reference template matching is too brittle.** Scaling, rotation, and stroke width variation make geometric comparison unreliable.
5. **Component merging works for nearby strokes but fails when the gap is large or the stroke is faint.**

## Future Directions (if revisited)

- **ML-based segmentation:** Use a pre-trained model (e.g., CRAFT for text detection, or a custom U-Net) to segment Nastaliq strokes.
- **Stroke-level analysis:** Instead of letter-level matching, analyze individual stroke quality (pressure, flow, curvature).
- **On-device processing:** TensorFlow.js or ONNX Runtime for mobile inference.
- **Expert feedback loop:** Collect Ahmad's corrections and train a personalized model.

## Files

- `pipeline.py` — Classical CV pipeline (abandoned approach)
- `main.py` — FastAPI app
- `references.py` — Reference image generation
- `static/index.html` — Mobile web UI
- `tests/` — 37 test cases (all passing at abandonment)
- `ARCHITECTURE.md`, `REQUIREMENTS.md`, `MVP_SCOPE.md`, `DECISION_LOG.md` — Design docs

---

*Project archived. Do not resume without ML-based approach.*
