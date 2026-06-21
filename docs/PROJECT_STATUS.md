# AVIS — Project Status & Context Tracker

> Living document for managing context across sessions. Update it as work lands.
> Source of truth for *design* stays `docs/DESIGN.md`; this file tracks *state*.
> Last updated: **2026-06-21**.

---

## 1. One-line status

End-to-end vertical slice works and is demo-ready: upload → detect → evidence graph →
rules → confidence routing → (optional VLM audit) → legal mapping → annotated evidence →
**interpretable React dashboard**. Helmet detection now runs on a **local model (zero API
calls)**; plate OCR works via **fast-alpr**; all 7 violation types are represented.
**Quality gates green:** 49 tests pass, ruff clean, ruff-format clean, mypy clean.

---

## 2. Architecture snapshot

```
upload (api/) → queue (quality gate → preprocess) → pipeline:
  detect (YOLO11 COCO)               core/detect
  → build Evidence Graph             core/graph     (single source of truth)
  → helmet attrs (LOCAL YOLO model)  core/detect    (no API; was Gemini)
  → plates (fast-alpr → Gemini fb)   core/plates
  → light state (HSV)                core/detect
  → load calibration zones           core/calibration  configs/<camera>.json
  → run rules (pure)                 core/rules
  → fuse scores + route + VLM audit  core/pipeline  (VLM = auditor only)
  → legal mapping                    core/legal
  → hash + annotate + persist        core/evidence + core/storage
React dashboard (frontend/) ← FastAPI (api/main.py) ← storage (SQLite/Postgres + files/MinIO)
```

Invariants held: VLM is an auditor (never the detector); only Tier A may auto-confirm;
abstain over guess; the Evidence Graph drives all reasoning; rules are pure/deterministic.

---

## 3. Violation coverage (vs the problem statement's 7)

| Violation | Tier | Status | How it's decided |
|---|---|---|---|
| Helmet non-compliance | A | ✅ Working, **offline** | Local 7-class YOLO model → rider helmet status; auto-confirm/VLM-skip |
| Triple riding | A | ✅ Working | Count `rides` edges ≥ 3; routed (VLM/human) unless very high fused |
| Seatbelt non-compliance | B | ✅ Implemented (gated) | `SEATBELT_CHECK=true` → speculative candidate → VLM verify; dropped if not confirmed |
| Stop-line crossing | C | ✅ Working w/ calibration | Vehicle ground-point in `stop_line` zone; never auto-confirm |
| Red-light violation | C | ✅ Working w/ calibration | Red light + vehicle past stop-line; candidate |
| Illegal parking | C | ✅ Working w/ calibration | Vehicle in `no_parking` zone; candidate |
| Wrong-side driving | D | ⚪ Inert by design | A single frame can't prove direction → abstains (needs video) |

Plate OCR (all types): ✅ fast-alpr (ONNX) + Indian-plate regex; Gemini fallback when empty.

---

## 4. Problem-statement task coverage

| Task | Status | Notes |
|---|---|---|
| Image preprocessing (low-light/blur/etc.) | ✅ | CLAHE + denoise + gamma; quality gate abstains on too-dark/blurry/over-exposed |
| Vehicle + road-user detection & classification | ✅ | YOLO11 COCO; rider/driver/pedestrian roles in the graph |
| Violation detection (7 types) | ✅ 6 active + 1 inert | see §3 |
| Violation classification + confidence | ✅ | per-source scores (detection/rule/attribute/vlm) → fused; tier-aware routing |
| License-plate detection + OCR | ✅ | fast-alpr + regex; Gemini fallback |
| Evidence generation (annotated + metadata + timestamps) | ✅ | annotated copy, SHA-256 hash, audit trail, created_at |
| Analytics & reporting (trends/search/summary) | ✅ | `/analytics`, charts, review queue, search filters |
| Performance evaluation (P/R/F1, etc.) | ⚙️ harness ready | `eval/` computes P/R/F1, ablation, OCR acc, latency — **needs labelled images in `data/eval/`** |
| Efficiency / scalability | ✅ design | modular monolith; Redis-worker + Postgres + MinIO documented scale-out |

---

## 5. Task board

**Done (this iteration)**
- [x] Local helmet model wired in (`models/helmet/best.pt`, 7-class) — helmet detection needs **zero** API calls.
- [x] Plate OCR fixed (root cause: missing `onnxruntime`) + per-char-confidence bug + Gemini fallback chain.
- [x] Seatbelt (Tier B) rule + speculative drop-on-negative adjudication (off by default).
- [x] Interpretability API: `GET /violations/{id}`, image dims on `/images/{id}`, extended `/runtime`.
- [x] New **React + Vite + Chart.js** dashboard with full interpretability + e-challan view.
- [x] Tests: 33 → **49**; ruff/format/mypy all clean.

**Backlog / next**
- [ ] Add a labelled `data/eval/` set and publish real P/R/F1 + ablation numbers.
- [ ] Persist the Evidence Graph (per image) to enable client-side bbox overlays in the detail view.
- [ ] Optional: seatbelt via a local classifier (avoid VLM quota) instead of VLM-only.
- [ ] Optional: ChromaDB legal-RAG bonus (static table stays load-bearing).
- [x] Docker: multi-stage build compiles `frontend/dist` in a node stage (one-command deploy).

---

## 6. Change log

- **2026-06-21**
  - Helmet: replaced per-rider Gemini classification with a local YOLO11 model run once on
    the full image; matches helmet boxes to riders by containment (head boxes have tiny IoU
    but high containment) and augments riders COCO missed. Fixes the free-tier rate-limit flood.
  - Plates: added `onnxruntime` (the missing piece that made fast-alpr silently return nothing);
    fixed `confidence`-is-a-list crash; added `GeminiPlateRecognizer` + `ChainPlateRecognizer`.
  - Seatbelt: new Tier-B rule (gated by `SEATBELT_CHECK`); `Candidate.speculative` + adjudication
    that **drops** unconfirmed guesses instead of flooding human review.
  - API: `GET /violations/{id}`, `width`/`height` on `GET /images/{id}`, `vlm_enabled` + thresholds on `/runtime`.
  - Frontend: full React rewrite (interpretable cards, confidence breakdown, route explainer,
    e-challan, audit trail, evidence hash, charts, review, search).
  - Quality: brought the whole repo to ruff/format/mypy clean (cleared pre-existing debt).
  - Config fix: `.env` had `GEMINI_MODEL=gGemma-4-31B` (invalid id) → `gemma-3-27b-it`
    (vision-capable; Gemma 3 free tier ~30 RPM / ~15,000 RPD, much higher than Flash).

---

## 7. Issue / error log (root causes)

| Symptom | Root cause | Fix |
|---|---|---|
| "VLM unavailable" flooding human review on busy images | ~14 Gemini calls/image (helmet ×N + verify ×N) > 10 req/min free limit | Local helmet model (0 calls) + helmet candidates `pre_verified` (skip 2nd call) + retry/backoff |
| Number plate never shown | `fast_alpr` installed but `onnxruntime` missing → ONNX models couldn't run → silent "no plate" | `pip install onnxruntime` (added to requirements) |
| fast-alpr crash `float() ... not 'list'` | OCR `confidence` is a per-character list | `_as_conf()` collapses list → mean |
| Dashboard "too raw" | vanilla HTML dumped enums | React dashboard with friendly labels, badges, breakdowns, e-challan |

---

## 8. Known honest limitations

- **Seatbelt (Tier B)** is genuinely unreliable from a traffic cam; it never auto-confirms and
  is dropped unless the VLM can substantiate it. Off by default to protect quota.
- **Wrong-side (Tier D)** is inert — direction needs video; a single frame abstains.
- **Tier C** (stop-line/red-light/parking) needs per-camera calibration (`configs/<camera>.json`);
  without it, those rules simply don't fire (no fabrication).
- **Eval numbers** require a labelled `data/eval/` set — not shipped, so we publish no fake metrics.
- **Gemini free tier** (~1,500/day, ~10/min): plate fallback + seatbelt are the only paths that
  can spend it; both are sparing/optional.

---

## 9. Setup & run (quick reference)

```powershell
# deps (one-time)
venv\Scripts\python.exe -m pip install -r requirements.txt          # incl. onnxruntime
cd frontend ; npm install ; npm run build ; cd ..                    # builds frontend/dist

# run (serves the built React app at http://127.0.0.1:8000)
venv\Scripts\python.exe -m uvicorn api.main:app --reload

# frontend dev mode (hot reload, proxies API to :8000)
cd frontend ; npm run dev

# quality gates
venv\Scripts\python.exe -m pytest -q
venv\Scripts\python.exe -m ruff check . ; venv\Scripts\python.exe -m ruff format --check .
venv\Scripts\python.exe -m mypy core/ api/
```

Key env (`.env`): `HELMET_WEIGHTS=models/helmet/best.pt`, `PLATE_PROVIDER=fastalpr`,
`LLM_PROVIDER=gemini`, `GEMINI_MODEL=gemini-2.5-flash`, `SEATBELT_CHECK=false`.
**Security:** rotate `GEMINI_API_KEY` (it was shared in chat); `.env` is gitignored.
