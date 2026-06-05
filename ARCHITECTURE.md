# Nastaliq Corrector — Architecture Document

## Project: nastaliq-corrector
**Version:** 1.0 (MVP)  
**Date:** 2026-06-03  
**Author:** Design Agent (Zakoota 🖋️)

---

## 1. Overview

The Nastaliq Corrector is a web-based tool that accepts a photo of handwritten Urdu Nastaliq calligraphy practice, analyzes it using classical computer vision techniques, and returns the same photo with colored visual annotations indicating geometric corrections.

**Architecture Style:** Simple server-rendered web app with a lightweight API backend. No microservices, no databases, no auth — single-user personal tool.

---

## 2. High-Level Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        Client (Browser)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐   │
│  │  Camera     │  │  Photo      │  │  Annotated Image    │   │
│  │  Capture    │  │  Upload     │  │  Display / Download│   │
│  │  (mobile)   │  │  (FormData) │  │  (PNG/JPEG overlay) │   │
│  └─────────────┘  └─────────────┘  └─────────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTPS (POST multipart/form-data)
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      Web Server (Backend)                      │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  API Layer (FastAPI / Flask / Express — minimal)     │    │
│  │  • POST /upload — accepts image, returns job_id      │    │
│  │  • GET  /result/:id  — returns annotated image       │    │
│  │  • POST /upload-simple — synchronous (MVP default)   │    │
│  └─────────────────────┬───────────────────────────────┘    │
│                        │                                     │
│                        ▼                                     │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  CV Pipeline (Python + OpenCV)                       │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │    │
│  │  │Preprocess│→│Segment   │→│Reference │→│Annotate  │ │    │
│  │  │         │  │Letters   │  │Compare   │  │& Render  │ │    │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ │    │
│  └──────────────────────────────────────────────────────┘    │
│                        │                                     │
│                        ▼                                     │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Reference Library (Static Assets)                   │    │
│  │  • SVG/PNG templates for each letter in standard     │    │
│  │    Nastaliq form                                     │    │
│  │  • Metadata: baseline y-pos, slant angle, proportions │    │
│  └──────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Data Flow

### 3.1 Upload → Annotate Flow (Synchronous — MVP Default)

```
User selects/captures photo
        │
        ▼
[Client] Resize/compress if > 2MB (client-side for speed)
        │
        ▼
[Client] POST /upload-simple (multipart/form-data)
        │
        ▼
[Server] Receive → validate (format, size, quality check)
        │
        ├─ Bad photo? → 400 error with friendly message
        │
        ▼
[Server] Preprocess: grayscale, denoise, deskew (optional), crop
        │
        ▼
[Server] Segment: find connected components → isolate letter blobs
        │
        ▼
[Server] Classify: match blob to reference letter (template matching / contour comparison)
        │
        ├─ Unrecognized? → flag as "unknown" (no annotation, continue)
        │
        ▼
[Server] Measure: compute baseline offset, slant angle, bounding box proportions
        │
        ▼
[Server] Compare against reference metadata
        │
        ▼
[Server] Annotate: draw overlays on original image
        │
        ▼
[Server] Return annotated image (PNG/JPEG) + metadata JSON
        │
        ▼
[Client] Display result (original + annotated side-by-side or toggle)
```

### 3.2 Quality Check Gate (Pre-Analysis)

```
Photo received
    │
    ▼
Check 1: Resolution ≥ 500x500? (too small → reject)
    │
    ▼
Check 2: Blur detection (Laplacian variance < threshold? → reject)
    │
    ▼
Check 3: Darkness (mean pixel value < threshold? → reject)
    │
    ▼
Check 4: Excessive glare (local brightness spikes? → warn, don't reject)
    │
    ▼
Pass → proceed to analysis
```

**Threshold Philosophy:**  
- Hard reject: Only truly unusable photos (extreme blur, pitch black, <200px resolution)  
- Soft pass: Accept borderline cases, even if analysis quality may suffer  
- This matches Ahmad's instruction: "be forgiving, don't reject most photos"

---

## 4. Component Details

### 4.1 Client (Frontend)

**Tech Options Considered:**

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| Vanilla HTML + JS | Fastest, no build step | Harder to maintain later | ✅ **Chosen for MVP** |
| React/Vue | Better UX, reusable components | Build complexity, overkill for MVP | Deferred to v2 |
| Flutter Web | Cross-platform future | Heavy, overkill for single web page | ❌ Rejected |

**MVP Client Spec:**
- Single HTML file with inline CSS/JS
- File input with `accept="image/*"` + `capture="environment"` for mobile camera
- Drag-and-drop on desktop
- Simple progress bar (spinner) during processing
- Side-by-side or toggle view for original vs annotated
- No frameworks, no build pipeline

### 4.2 Backend API

**Tech Options Considered:**

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| Python + FastAPI | Native OpenCV integration, async, fast | None significant | ✅ **Chosen** |
| Python + Flask | Simple, familiar | Synchronous by default, slower | ❌ Rejected |
| Node.js + Express | JS ecosystem, fast I/O | OpenCV bindings less mature | ❌ Rejected |
| Serverless (Vercel/Netlify) | No server management | 10s timeout risk, image processing heavy | ❌ Rejected |

**MVP API Spec:**
- Single endpoint: `POST /upload-simple`
- Request: `multipart/form-data` with `image` field
- Response: `image/png` (annotated image) or `application/json` with error
- No async job queue (single-user, synchronous is fine)
- No database, no storage — process in memory, return result, discard

### 4.3 CV Pipeline (Core)

**Tech Stack:** Python 3.11+, OpenCV 4.x, NumPy

| Stage | Technique | Details |
|---|---|---|
| **Preprocess** | Grayscale, Gaussian blur, threshold (Otsu adaptive) | Prepare image for contour detection |
| **Deskew** (optional) | Hough line transform or projection profile | Correct up to ~15° rotation |
| **Segment** | Connected components + contour filtering | Find letter blobs; filter by size (remove specks, noise) |
| **Classify** | Template matching (cv2.matchTemplate) OR contour shape comparison (Hu moments) | Match blob to reference letter |
| **Measure** | Pixel-level analysis: bounding box, minAreaRect, projection profiles | Compute baseline, slant, proportions |
| **Annotate** | OpenCV drawing: cv2.line, cv2.arrowedLine, cv2.polylines | Overlay on original image |

**Reference Matching Approach:**

Option A: **Template Matching** (cv2.matchTemplate)
- Pros: Simple, built-in, works for known shapes
- Cons: Sensitive to rotation, scale, stroke thickness
- Best for: MVP when letters are roughly consistent size

Option B: **Feature Matching** (ORB/SIFT + homography)
- Pros: Rotation/scale invariant
- Cons: Overkill, may not work well on handwritten strokes
- Best for: Not MVP

Option C: **Contour Comparison** (Hu moments + shape context)
- Pros: Scale/rotation invariant, lightweight
- Cons: Less precise than template matching
- Best for: Fallback when template fails

**Chosen approach (MVP):** Option A (Template Matching) as primary, with Option C (Contour Comparison) as fallback for unrecognized shapes.

### 4.4 Reference Library

- Static directory of reference images: one PNG/SVG per letter
- Metadata JSON per letter: `{"baseline_y": 0.65, "slant_angle": 25, "aspect_ratio": 1.8, ...}`
- Pre-generated using computer-generated Nastaliq font (Jameel Noori Nastaleeq or similar)
- Simple directory structure: `references/{letter}/{size}/{slant}.png`

---

## 5. Infrastructure

| Component | MVP Choice | Notes |
|---|---|---|
| Hosting | Local machine / Raspberry Pi / cheap VPS | Single user, no traffic |
| Server | Python + FastAPI, uvicorn | Run behind nginx if exposed to internet |
| Storage | None (ephemeral) | Images processed in memory, not stored |
| CDN | Not needed | Single user |
| SSL | Let's Encrypt (if exposed) or self-signed | Required for camera access on HTTPS |
| Domain | Optional | Can use IP + port for personal use |

---

## 6. Unknowns / Risks

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| **R1: Stroke thickness variation** | Template matching fails if Ahmad's pen thickness differs significantly from reference | Medium | Add multiple reference templates per letter (thin/medium/thick strokes). Use contour matching as fallback. |
| **R2: Connected letter detection** | Classical CV struggles with cursive/connected Nastaliq letters | High | MVP scope is **isolated letters only**. Defer connected words to v2+ with ML. |
| **R3: Photo quality edge cases** | Shadows, uneven lighting, paper texture can fool thresholding | Medium | Preprocess with adaptive thresholding + CLAHE contrast enhancement. Accept imperfect results. |
| **R4: Slant angle ambiguity** | Nastaliq has natural slant; distinguishing "correct" vs "incorrect" slant is subjective | Medium | Calibrate reference slant angle per letter from standard font. Allow ±5-10° tolerance. |
| **R5: Baseline detection on skewed photos** | If photo is not top-down, baseline computation is wrong | Medium | Add auto-deskew step (FR-11). If deskew fails, warn user instead of producing wrong annotations. |
| **R6: Processing speed > 10s** | OpenCV operations on high-res images may exceed 10s on modest hardware | Medium | Downsample image for analysis (keep display resolution). Optimize contour operations. |
| **R7: Letter classification errors** | Misidentifying a ب as a ت, etc. | Medium | Return confidence score. Low confidence = don't annotate (avoid wrong corrections). |
| **R8: Reference font vs handwritten style mismatch** | Computer font doesn't capture handwritten nuance | Low (MVP) | Ahmad confirmed computer-generated is acceptable for MVP. |
| **R9: Mobile browser camera access** | iOS Safari has restrictions on `<input capture>` | Low | Test on target devices. Use `accept="image/*"` as fallback. |
| **R10: No persistent storage means no history** | Can't review past corrections | Low (MVP) | Out of scope for MVP. User can save images manually. |

---

## 7. Performance Budget

| Operation | Target Time | Notes |
|---|---|---|
| Upload + transfer | 1-2s | Depends on photo size, 4G connection |
| Quality validation | < 500ms | Simple CV checks |
| Preprocessing | 1-2s | Grayscale, denoise, threshold |
| Segmentation | 1-2s | Connected components |
| Classification + measurement | 2-4s | Template matching per letter |
| Annotation rendering | 1-2s | Drawing overlays |
| **Total end-to-end** | **≤ 10s** | **Hard requirement** |

---

## 8. Extensibility: Connected Letters (v3+)

The current architecture is intentionally **pipeline-pluggable**. Upgrading from isolated-letter classical CV to connected-word ML analysis requires swapping only the CV pipeline module — no API changes, no frontend rewrite, no database migration.

### Current v1 Pipeline
```
[Upload] → Quality Gate → Preprocess → Connected Components → Template Matching → Measure → Annotate → Return
```

### Future v3+ Pipeline (Connected Words)
```
[Upload] → Quality Gate → Preprocess → Text Detection (CRAFT/DBNet) → Text Recognition (TrOCR/custom) → Word Segmentation → Letter-wise Comparison → Annotate → Return
```

### What Changes
| Component | v1 (Current) | v3+ (Connected) |
|---|---|---|
| Segmentation | Connected components + size filter | Text detection model (e.g., CRAFT, DBNet) |
| Classification | Template matching / Hu moments | CNN/Transformer sequence model |
| Reference library | 33 isolated PNGs + JSON | 4 forms per letter (isolated, initial, medial, final) + ligature references |
| Baseline detection | Bounding box bottom edge | Projection profile + script-aware baseline estimation |
| Annotation logic | Per-blob overlay | Per-character overlay within word bounding boxes |

### What Stays the Same
- API endpoints and request/response contracts
- Frontend upload, display, and toggle logic
- Quality gate (preprocessing + blur/darkness checks)
- Annotation renderer (OpenCV drawing functions)
- Reference library directory structure (just more entries)

### Why We Document This Now
Proves the monolith decision is not a dead end. The CV pipeline is a replaceable module. When v3 arrives, we write `ml_pipeline.py` instead of `classical_pipeline.py`, import it in `main.py`, and the rest of the system is unchanged.

---

*Next: Ahmad, please review and approve these specs.*
