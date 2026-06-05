# Nastaliq Corrector — Decision Log

## Project: nastaliq-corrector
**Version:** 1.0 (MVP)  
**Date:** 2026-06-03  
**Author:** Design Agent (Zakoota 🖋️)

---

## 1. Tech Stack: Backend Framework

**Decision:** Python + FastAPI

**Options Considered:**

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| **A. Python + FastAPI** | Native OpenCV, async by default, automatic API docs, modern | Slightly more boilerplate than Flask | ✅ **Chosen** |
| **B. Python + Flask** | Minimal, familiar, huge ecosystem | Sync by default, less performant | ❌ Rejected — async matters for image processing |
| **C. Node.js + Express** | Fast I/O, same language as frontend | OpenCV bindings (opencv4nodejs) less mature, less documentation | ❌ Rejected — CV is the core, Python ecosystem is superior |
| **D. Go + Gin** | Fast, compiled, efficient | OpenCV bindings exist but are less mature than Python; steeper learning curve for CV work | ❌ Rejected — unnecessary complexity |

**Why FastAPI:**
- OpenCV is a first-class citizen in Python. The Python ecosystem (scikit-image, Pillow, NumPy) is unmatched for classical CV.
- Async support means the server can handle concurrent uploads without blocking, even if we only have one user (future-proofing).
- Auto-generated OpenAPI/Swagger docs are nice for debugging.
- FastAPI is the modern standard; Flask is legacy for new projects.

**Trade-off:** We accept Python's heavier memory footprint and slower startup vs. Node.js because the CV pipeline is the bottleneck, not the web framework.

---

## 2. Tech Stack: Frontend Approach

**Decision:** Vanilla HTML + CSS + JavaScript (single page, no framework)

**Options Considered:**

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| **A. Vanilla HTML/JS** | Fastest to build, no build step, no dependencies, single file | Harder to scale UI complexity | ✅ **Chosen for MVP** |
| **B. React (Vite)** | Component model, better UX patterns, ecosystem | Build step, dependencies, overkill for one page | ❌ Deferred to v2 if UI grows |
| **C. Vue 3 (CDN)** | Lightweight, progressive, can start simple | Still adds complexity vs. vanilla | ❌ Rejected — unnecessary for single page |
| **D. Flutter Web** | Cross-platform future, mobile-native feel | Heavy bundle, overkill, poor web performance | ❌ Rejected |

**Why Vanilla:**
- The MVP UI is literally: upload button, spinner, image display. That's 3 DOM elements.
- No build pipeline = no webpack/vite config issues, no dependency updates, no "it works on my machine."
- Ahmad said "whatever gets to a working demo fastest" — this is fastest.
- Can always migrate to React/Vue in v2 if we add comparison views, history, settings, etc.

**Trade-off:** We accept less polished UX patterns (no virtual DOM, no state management) because the UI is trivial today.

---

## 3. Letter Detection: Template Matching vs. Feature Detection

**Decision:** Template Matching (cv2.matchTemplate) as primary, with Contour Comparison (Hu moments) as fallback.

**Options Considered:**

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| **A. Template Matching** | Simple, fast, built-in, works well for consistent shapes | Sensitive to rotation, scale, stroke thickness | ✅ **Primary (MVP)** |
| **B. Feature Matching (ORB/SIFT)** | Rotation/scale invariant, more robust | Overkill, may not work well on low-texture handwritten strokes; patent issues with SIFT | ❌ Not for MVP |
| **C. Contour Comparison (Hu moments)** | Scale/rotation/translation invariant, lightweight | Less precise, can confuse similar letters (ب vs ت) | ✅ **Fallback** |
| **D. ML Classification (CNN)** | High accuracy, learns stroke variation | Requires training data, model size, inference time, overkill for 33 letters | ❌ Deferred to v3 |

**Why Template Matching + Fallback:**
- For isolated letters on white paper, template matching is surprisingly effective. The shapes are consistent enough.
- We add a fallback (contour comparison) for cases where template matching fails (different pen thickness, slight rotation).
- ML is the future, but it's not needed for 33 isolated letters with classical CV.

**Trade-off:** We accept lower accuracy on edge cases (rotated photos, thick pens) to avoid ML complexity. If classical CV hits a ceiling, v3 will switch to ML.

---

## 4. Reference Standard: Pre-Generated vs. Dynamic

**Decision:** Pre-generated static reference library (PNG + JSON metadata)

**Options Considered:**

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| **A. Pre-generated PNGs + JSON** | Fast lookup at runtime, deterministic, simple | Requires manual regeneration if style changes | ✅ **Chosen** |
| **B. Dynamic generation (font rendering at runtime)** | Always consistent, no storage needed | Slower (font rendering per request), requires font library | ❌ Rejected — unnecessary overhead |
| **C. Hand-drawn references by expert** | Authentic, captures real nuance | Requires expert time, not reproducible, inconsistent | ❌ Rejected — Ahmad said computer-generated is acceptable |
| **D. SVG vector templates** | Scalable, small file size, can adjust stroke width | More complex to render with OpenCV (rasterizes anyway) | ❌ Rejected — PNG is simpler for template matching |

**Why Pre-Generated:**
- Template matching needs raster images. Pre-generating them at multiple sizes removes runtime font rendering.
- We can generate references from a standard Nastaliq font (Jameel Noori Nastaleeq, Urdu Nastaliq Unicode, etc.) using a simple script.
- Easy to version control: if we change the reference standard, we regenerate the library.

**Trade-off:** We accept storage of ~100 reference images (33 letters × 3 sizes) vs. zero storage with dynamic generation. Storage is cheaper than CPU.

---

## 5. Annotation Style: Visual-Only vs. Text Labels

**Decision:** Colored lines and arrows ONLY. No text labels.

**Options Considered:**

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| **A. Visual-only (lines/arrows)** | Clean, minimal, language-agnostic, matches Ahmad's preference | User must learn what each color means (but it's intuitive) | ✅ **Chosen** |
| **B. Text labels + icons** | Explicit, self-documenting, accessible | Clutters image, requires localization (Urdu/English), distracts from the calligraphy | ❌ Rejected — Ahmad explicitly said no text labels |
| **C. Tooltip/hover labels** | Best of both worlds — clean image, info on demand | Requires interactive UI, not possible on static image export | ❌ Rejected for v1 (could be v2 feature) |

**Why Visual-Only:**
- Ahmad explicitly requested this in the interview: "Colored lines/arrows only. NO text labels."
- Nastaliq is visual art; text labels would visually pollute the feedback.
- Colors can be intuitive: red = stop/fix this, green = good target, blue = direction, orange = attention.
- A simple legend (outside the image) can explain colors if needed, but not on the image itself.

**Trade-off:** First-time users may need a legend to understand colors. We'll add a one-time onboarding legend below the image, not overlaid on it.

---

## 6. Processing Location: Server vs. Client

**Decision:** Server-side processing (Python + OpenCV)

**Options Considered:**

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| **A. Server-side (Python/OpenCV)** | Full OpenCV feature set, no browser limitations, easier to debug | Requires server, internet dependency, latency | ✅ **Chosen for MVP** |
| **B. Client-side (TensorFlow.js + OpenCV.js)** | No server needed, privacy (image never leaves device), instant | OpenCV.js is a subset of OpenCV, TF.js model needed, performance varies by device | ❌ Deferred to v3 |
| **C. Hybrid (client preprocess + server analyze)** | Reduces upload size, faster | More complex, two codebases | ❌ Rejected — unnecessary for MVP |

**Why Server-Side:**
- OpenCV.js exists but is a subset and harder to work with. The full Python OpenCV ecosystem is mature.
- No need to optimize for privacy (single user, personal use) or server costs (one user = one cheap VPS).
- Ahmad said "cloud processing acceptable for MVP."

**Trade-off:** We accept internet dependency and server maintenance burden. If Ahmad wants to practice without internet, v3 can explore client-side processing.

---

## 7. Quality Check: Forgiving vs. Strict

**Decision:** Forgiving quality gate — reject only truly unusable photos.

**Options Considered:**

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| **A. Forgiving (reject only extreme cases)** | User-friendly, fewer interruptions, matches Ahmad's instruction | May process low-quality photos with poor results | ✅ **Chosen** |
| **B. Strict (reject borderline cases)** | Higher analysis accuracy, consistent results | Frustrating user experience, rejects many casual photos | ❌ Rejected — Ahmad said "don't reject most photos" |
| **C. No quality check** | Zero friction, never rejects | Risk of processing completely useless images, wasting time | ❌ Rejected — some guardrails needed |

**Why Forgiving:**
- Ahmad explicitly said: "Reject bad photos, but threshold should NOT be too sensitive — be forgiving, don't reject most photos."
- A frustrated user who can't upload a slightly blurry photo is worse than a user who gets mediocre annotations on a mediocre photo.
- We can always add a "quality warning" (soft message: "Photo is a bit dark, results may be less accurate") instead of a hard rejection.

**Trade-off:** We accept occasional poor analysis results on low-quality photos. User experience > accuracy on edge cases for MVP.

**Implementation:**
- Hard reject: Resolution < 200px, Laplacian variance < 50 (very blurry), mean brightness < 20 (pitch black)
- Soft warning: Resolution < 500px, brightness < 50, slight blur detected — process anyway, add warning message

---

## 8. Letter Scope: 33 vs. Full Alphabet + Forms

**Decision:** 33 disconnected (isolated) letters only for v1.

**Options Considered:**

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| **A. 33 isolated letters** | Manageable, classical CV works well, covers fundamentals | Doesn't cover connected forms, diacritics, or ligatures | ✅ **Chosen for MVP** |
| **B. Full Urdu alphabet (52+ characters including connected forms)** | Comprehensive, more useful for real practice | Connected forms are extremely hard to segment with classical CV | ❌ Rejected — too hard for v1 |
| **C. 33 + diacritics** | Adds vowel marks, more complete | Diacritics are small and hard to detect/classify reliably | ❌ Deferred to v2 |
| **D. Common words instead of letters** | Practical, real-world use | Requires word segmentation — ML territory | ❌ Deferred to v3 |

**Why 33 Isolated Letters:**
- Isolated letters are the building blocks of Nastaliq. Master these before connected script.
- Connected Nastaliq letters overlap, share strokes, and change shape based on position. This is a hard problem even for ML models (state-of-the-art Urdu OCR is still developing).
- Classical CV can isolate blobs for disconnected letters. It cannot reliably segment connected words.

**Trade-off:** We accept a narrower but achievable scope. The MVP delivers real value on fundamentals rather than failing on ambitious full-text analysis.

---

## 9. Architecture: Monolith vs. Microservices

**Decision:** Single monolithic server (FastAPI app + CV pipeline in one process).

**Options Considered:**

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| **A. Monolith (single FastAPI app)** | Simple, one codebase, easy to deploy, no network overhead | Tight coupling, harder to scale individual parts | ✅ **Chosen for MVP** |
| **B. Microservices (API + CV worker + queue)** | Scalable, independent deployment, resilient | Complex, requires message queue, overkill for 1 user | ❌ Rejected — massive overkill |
| **C. Serverless functions** | No server management, scales to zero | 10s timeout risk, cold start, image processing heavy | ❌ Rejected — processing may exceed function limits |

**Why Monolith:**
- One user = one server. No scaling concerns.
- No need for a message queue, worker processes, or container orchestration.
- Single deployment: `python main.py` and it works.

**Trade-off:** If we ever scale to multiple users (unlikely for this project), we'll need to refactor. But YAGNI — You Ain't Gonna Need It.

---

## 10. Summary: Decisions at a Glance

| # | Decision | Chosen | Key Reason |
|---|---|---|---|
| 1 | Backend framework | Python + FastAPI | OpenCV ecosystem, async support |
| 2 | Frontend approach | Vanilla HTML/JS | Fastest to working demo |
| 3 | Letter detection | Template matching + contour fallback | Simple, fast, sufficient for 33 letters |
| 4 | Reference standard | Pre-generated PNGs + JSON | Fast lookup, deterministic |
| 5 | Annotation style | Visual-only (no text) | Ahmad's explicit preference |
| 6 | Processing location | Server-side (Python) | Full OpenCV, single user, cloud OK |
| 7 | Quality check | Forgiving | Ahmad: "don't reject most photos" |
| 8 | Letter scope | 33 isolated letters | Achievable with classical CV |
| 9 | Architecture | Monolith | One user, no need for complexity |
| 10 | Storage | None (ephemeral) | Privacy, no history needed for MVP |

## 11. Extensibility Note: Connected Letters (v3+)

**Decision:** Monolith architecture is compatible with future ML pipeline swap.

**Options Considered:**
- Microservices now (overkill) vs Monolith now with documented upgrade path
- Chosen: Monolith with pipeline-as-module design

**Why:** The CV pipeline is a pluggable module. Current `classical_pipeline.py` can be replaced by `ml_pipeline.py` in v3 without touching the API layer, frontend, or annotation renderer. See ARCHITECTURE.md Section 8 for full details.

---

*Next: Ahmad, please review and approve these specs.*
