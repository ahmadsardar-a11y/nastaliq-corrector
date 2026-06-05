# Nastaliq Corrector — Requirements Document

## Project: nastaliq-corrector
**Version:** 1.0 (MVP)  
**Date:** 2026-06-03  
**Author:** Design Agent (Zakoota 🖋️)

---

## 1. Functional Requirements

### 1.1 Photo Capture & Upload
| ID | Requirement | Priority |
|---|---|---|
| FR-1 | User can upload a photo from device gallery or camera (mobile-first) | [MUST] |
| FR-2 | User can capture photo directly via camera on mobile devices | [MUST] |
| FR-3 | System validates photo quality (blur, darkness, excessive glare) and rejects unusable images with a clear message | [MUST] |
| FR-4 | Validation threshold is forgiving — should accept common smartphone photos with minor lighting issues | [MUST] |
| FR-5 | Supported formats: JPEG, PNG | [MUST] |
| FR-6 | Maximum file size: 10 MB (arbitrary limit for MVP) | [SHOULD] |

### 1.2 Preprocessing
| ID | Requirement | Priority |
|---|---|---|
| FR-7 | Auto-orient photo based on EXIF data | [MUST] |
| FR-8 | Convert to grayscale for analysis | [MUST] |
| FR-9 | Apply noise reduction (Gaussian blur / median filter) to handle photo artifacts | [MUST] |
| FR-10 | Detect and crop to the writing region (remove table, background clutter) | [SHOULD] |
| FR-11 | Deskew if photo is taken at slight angle (up to ~15°) | [SHOULD] |

### 1.3 Letter Detection & Analysis
| ID | Requirement | Priority |
|---|---|---|
| FR-12 | Detect individual letters from the submitted writing | [MUST] |
| FR-13 | **Initial letter set:** Basic disconnected letters: ا, ب, پ, ت, ث, ج, چ, ح, خ, د, ڈ, ذ, ر, ز, ژ, س, ش, ص, ض, ط, ظ, ع, غ, ف, ق, ک, گ, ل, م, ن, و, ہ, ی, ء | [MUST] |
| FR-14 | Compare detected letters against computer-generated reference standard | [MUST] |
| FR-15 | Measure geometric properties: baseline alignment, slant angle, letter proportions (height/width ratios), stroke connections | [MUST] |
| FR-16 | Tolerance thresholds: small deviations (within ~5-10%) should NOT trigger annotations to avoid over-correction | [SHOULD] |

### 1.4 Annotation / Output
| ID | Requirement | Priority |
|---|---|---|
| FR-17 | Overlay colored lines and arrows on the original photo to indicate corrections | [MUST] |
| FR-18 | **NO text labels** on annotations — visual cues only (per Ahmad's preference) | [MUST] |
| FR-19 | Annotation types: <br>• Red line = correct baseline position <br>• Blue arrow = slant correction direction <br>• Green dotted outline = correct proportions <br>• Orange line = missing / incorrect stroke connection | [MUST] |
| FR-20 | Return annotated image within 10 seconds of upload (success criteria) | [MUST] |
| FR-21 | Display original image side-by-side with annotated image for comparison | [SHOULD] |
| FR-22 | Allow user to download/save the annotated image | [NICE-TO-HAVE] |
| FR-23 | Allow user to toggle annotations on/off to see the clean original | [NICE-TO-HAVE] |

### 1.5 User Experience
| ID | Requirement | Priority |
|---|---|---|
| FR-24 | Web interface is responsive and works on mobile browsers (primary target) | [MUST] |
| FR-25 | Works on desktop browsers (secondary) | [SHOULD] |
| FR-26 | Clear loading/processing indicator during analysis | [MUST] |
| FR-27 | Friendly error messages if photo is rejected or processing fails | [MUST] |
| FR-28 | No user accounts or login required (MVP) | [MUST] |

---

## 2. Non-Functional Requirements

| ID | Requirement | Priority |
|---|---|---|
| NFR-1 | **Performance:** End-to-end processing (upload → annotated image) ≤ 10 seconds on a typical 4G connection and mid-range server | [MUST] |
| NFR-2 | **Accuracy:** Baseline and slant detection accuracy ≥ 80% on clean, well-lit photos of isolated letters | [MUST] |
| NFR-3 | **Accuracy:** Proportion detection accuracy ≥ 70% for MVP (acknowledged as hard problem) | [SHOULD] |
| NFR-4 | **Reliability:** Graceful degradation — if analysis fails on a specific letter, still return partial annotations for the rest | [SHOULD] |
| NFR-5 | **Scalability:** Single-user personal use only. No need for horizontal scaling in MVP. | [MUST] |
| NFR-6 | **Security:** No personal data collection. Photos are processed and discarded (no storage). | [MUST] |
| NFR-7 | **Accessibility:** Basic color-safe annotations (don't rely solely on color; line styles differ too) | [SHOULD] |
| NFR-8 | **Browser Support:** Latest Chrome, Safari, Firefox on mobile and desktop | [MUST] |
| NFR-9 | **Offline:** Not required for MVP (cloud processing acceptable) | [MUST] |
| NFR-10 | **Privacy:** All processing happens server-side; no image data sent to third-party APIs | [MUST] |

---

## 3. Constraints & Assumptions

| # | Constraint / Assumption |
|---|---|
| 1 | User writes on plain white/light paper with dark ink (black, blue, or similar) |
| 2 | Letters are written in isolation (not connected words) for MVP |
| 3 | Photo is taken from roughly top-down perspective (not extreme angles) |
| 4 | Writing is large enough to be legible in the photo (minimum ~100px height per letter) |
| 5 | Classical CV approach only — no ML/DL model training for MVP |
| 6 | Computer-generated reference images are acceptable as standard |
| 7 | Single user (Ahmad) — no multi-tenancy, auth, or account management needed |

---

## 4. Open Questions (Pending Ahmad Review)

1. **Annotation density:** If multiple errors exist on one letter, how many annotations should be shown simultaneously? (risk: visual clutter)
2. **Reference generation:** Should we pre-generate a reference image library, or generate reference shapes dynamically on-the-fly?
3. **Colorblindness:** Should we add non-color visual cues (dashed vs solid lines) now, or defer to v2?
4. **Arabic vs Urdu Nastaliq:** Should the initial letter set include Arabic-specific letters (like ك instead of ک), or strict Urdu-only?

---

*Next: Ahmad, please review and approve these specs.*
