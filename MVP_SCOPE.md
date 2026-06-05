# Nastaliq Corrector — MVP Scope & Roadmap

## Project: nastaliq-corrector
**Version:** 1.0 (MVP)  
**Date:** 2026-06-03  
**Author:** Design Agent (Zakoota 🖋️)

---

## 1. Philosophy

Build the smallest thing that delivers value. Ahmad uploads a photo of his calligraphy practice and gets back visual corrections. Everything else is a nice-to-have that can wait.

**MVP Success =** Ahmad can practice a basic disconnected letter (e.g., ب), take a photo, and see where his baseline, slant, or proportions are off — all within 10 seconds.

---

## 2. What Is IN v1 (MVP)

### Core Flow (The "Happy Path")
1. User opens web page on mobile
2. Taps "Take Photo" or selects from gallery
3. Photo uploads to server
4. Server checks quality (forgiving — rejects only truly bad photos)
5. Server preprocesses the image (grayscale, denoise, threshold)
6. Server finds letter blobs in the image
7. Server matches each blob to a reference letter
8. Server measures: baseline, slant, proportions
9. Server draws colored annotations on the original photo
10. Annotated image displayed to user

### In Scope — Technical

| Feature | Detail |
|---|---|
| **Web UI** | Single-page HTML, mobile-first, responsive |
| **Camera input** | `<input capture>` on mobile, file picker fallback |
| **Image upload** | Multipart POST, up to 10MB, JPEG/PNG |
| **Quality gate** | Forgiving blur/darkness/resolution checks |
| **Preprocessing** | Grayscale, Gaussian denoise, Otsu thresholding |
| **Letter segmentation** | Connected components + size filtering |
| **Letter classification** | Template matching against reference images |
| **Geometric measurement** | Baseline position, slant angle (minAreaRect), bounding box proportions |
| **Annotation rendering** | Colored lines/arrows overlaid on original image (NO text labels) |
| **Reference library** | Static PNGs generated from computer Nastaliq font + metadata JSON |
| **Letter set** | 33 basic disconnected Urdu letters (see full list below) |
| **Response time** | ≤ 10 seconds end-to-end |
| **Error handling** | Friendly messages for bad photos, unrecognized letters, processing failures |

### In Scope — Letters (v1 Set)

ا ب پ ت ث ج چ ح خ د ڈ ذ ر ز ژ س ش ص ض ط ظ ع غ ف ق ک گ ل م ن و ہ ی ء

(33 disconnected letters — the "building blocks" of Nastaliq)

### In Scope — Annotations (v1 Types)

| Annotation | Visual | Meaning |
|---|---|---|
| Baseline marker | Red horizontal line | Where the baseline should be |
| Slant correction | Blue arrow | Direction to adjust slant |
| Proportion guide | Green dotted rectangle | Correct height/width ratio |
| Stroke connection | Orange line | Missing or incorrect connection point |

---

## 3. What Is OUT of v1 (Deferred)

### Deferred to v2 (Near-Term, ~1-2 months after MVP)

| Feature | Rationale for Deferral |
|---|---|
| **Connected words / full sentences** | Classical CV cannot reliably segment connected Nastaliq. Requires ML/segmentation models. |
| **Diacritics (zer, zabar, pesh, tashdeed)** | Adds complexity to segmentation and reference matching. Core letters first. |
| **Arabic letter variants** (e.g., ك vs ک, ي vs ی) | Urdu-specific set is enough for MVP. Arabic support is a data augmentation problem. |
| **Auto-deskew** | Nice-to-have but not critical. Ask user to take photo straight on. |
| **Auto-crop to writing region** | Manual cropping or asking user to frame properly is acceptable for MVP. |
| **Side-by-side comparison view** | Single annotated image is sufficient. Toggle is nice but not core value. |
| **Download/save button** | User can use browser "Save Image" context menu. |
| **Basic user preferences** | e.g., annotation color theme, tolerance strictness |
| **Simple progress tracking** | Store last N results in localStorage (no server storage) |

### Deferred to v3 (Mid-Term, ~3-6 months)

| Feature | Rationale for Deferral |
|---|---|
| **ML-based analysis** (CNN/Transformer for letter recognition) | Classical CV may hit accuracy ceiling. ML is the escape hatch. |
| **Aesthetic judgment** (qalam pressure, stroke flow, artistic quality) | Requires expert system or trained model. Not geometric. |
| **Full word / sentence analysis** | Connected script needs ML segmentation (CRAFT, etc.) |
| **Multi-user support** | Single user (Ahmad) only. |
| **User accounts / auth** | Not needed for personal tool. |
| **Progress tracking / history** | Requires database + storage. Can be done with localStorage first. |
| **Practice mode / guided exercises** | Product feature, not core correction tool. |
| **Social sharing** | Export image + manual share is fine. |
| **Native mobile app** (iOS/Android) | Web app works. Native only if web performance is inadequate. |
| **Offline / on-device processing** (WebAssembly, TensorFlow.js) | Cloud processing is acceptable for MVP. |
| **Expert feedback loop** (Ahmad rates accuracy, system learns) | Requires data collection and ML pipeline. |
| **Multiple Nastaliq styles** (Pakistani, Iranian, etc.) | Different references per style. Pakistani Urdu standard first. |

### Deferred to v4+ (Long-Term / Maybe Never)

| Feature | Rationale |
|---|---|
| **Real-time video correction** (point camera at writing, see corrections live) | Extremely hard, requires real-time CV + mobile GPU. |
| **3D stroke analysis** (qalam angle, pressure depth) | Requires specialized hardware or multi-camera setup. |
| **Community features** (share work, get feedback from others) | Social product, not personal tool. |
| **Integration with calligraphy learning platforms** | Partnership/integration work. |
| **AI-generated personalized practice plans** | Requires user history + pedagogical model. |

---

## 4. Release Criteria

### v1.0 (MVP) — "First Stroke"
- [ ] Web page loads on mobile Safari and Chrome
- [ ] Camera capture works on iOS and Android
- [ ] Uploads process and return result in < 10 seconds
- [ ] All 33 disconnected letters have reference images
- [ ] At least baseline and slant annotations are visible and correct 80% of the time on clean photos
- [ ] Forgiving photo quality check (doesn't reject 90% of casual photos)
- [ ] Ahmad can use it for his daily practice

### v2.0 — "Connected Script"
- [ ] Side-by-side comparison view
- [ ] Download button
- [ ] Toggle annotations on/off
- [ ] Auto-deskew + auto-crop
- [ ] Diacritics support
- [ ] LocalStorage history (last 20 sessions)

### v3.0 — "Smart Corrector"
- [ ] ML-based letter recognition (accuracy > 90%)
- [ ] Connected word analysis
- [ ] Aesthetic judgment (basic stroke quality)
- [ ] Multiple Nastaliq styles
- [ ] On-device processing option (TF.js / WASM)

---

## 5. Scope Decision Log

| Decision | Options | Chosen | Why |
|---|---|---|---|
| Isolated vs connected letters | Isolated letters only (v1) / Full words (v1) | Isolated | Classical CV cannot segment connected Nastaliq reliably. Full words need ML. |
| 33 vs 52+ letters | 33 basic (v1) / Full Urdu + Arabic (v1) | 33 basic | Covers all disconnected forms. Connected forms (like بـ, ـبـ, ـب) deferred to v2. |
| Text labels on annotations | No text (v1) / Text labels (v1) | No text | Ahmad explicitly prefers visual-only annotations. |
| Synchronous vs async API | Sync (single endpoint) / Async (job queue) | Synchronous | Single user, no need for queue complexity. |
| Server vs client processing | Server-side (cloud) / Client-side (WASM) | Server-side | OpenCV in Python is mature. WASM/TF.js is v3 exploration. |
| Store vs ephemeral | No storage (process & discard) / Save results | Ephemeral | No history needed for MVP. Privacy win. |
| Strict vs forgiving quality check | Forgiving (v1) / Strict (v1) | Forgiving | Ahmad explicitly said: "don't reject most photos." |

---

*Next: Ahmad, please review and approve these specs.*
