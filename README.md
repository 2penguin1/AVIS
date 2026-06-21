# AVIS — Automated Violation Intelligence System (Gridlock)

Detects, classifies, and documents traffic violations from **single** images. Hybrid:
deterministic CV detects; a VLM (Gemini, free tier) only *verifies* ambiguous cases and
*abstains* when a photo can't prove a violation. See [`docs/DESIGN.md`](docs/DESIGN.md)
and [`docs/ROADMAP.md`](docs/ROADMAP.md).

## Quick start (local dev — zero infra)

```bash
python -m venv .venv && .venv\Scripts\activate    # PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env                              # defaults are fine (SQLite + no VLM)
uvicorn api.main:app --reload                     # open http://127.0.0.1:8000
```

Upload a traffic image on the dashboard, or `POST /images` (multipart `file`). First run
downloads the YOLO weights automatically.

## Full stack (Postgres + Redis + MinIO)

```bash
docker compose up --build
```

## Run the checks

```bash
pytest -q            # pure unit tests (rules, scene graph) — no models needed
ruff check . && mypy core/ api/
```

## Status (vertical slice)

Implemented: upload → **quality gate** (abstain on unusable images) → **preprocessing**
(CLAHE/denoise/low-light) → YOLO detection → evidence graph → **traffic-light state** →
**Tier-A** rules (helmet, triple-riding) + **Tier-C** calibration rules (stop-line,
red-light, illegal-parking) → confidence fusion + tier-aware routing (auto-confirm / VLM /
human / abstain) → **license-plate recognition** (fast-alpr + Indian-plate regex) → legal
mapping → annotated evidence → **analytics dashboard + human-review queue (audit trail) +
searchable records**. Gemini VLM verification is wired and tested.

Tier-C rules need a camera calibration file in `configs/<camera_id>.json` (sample:
`configs/cam_demo.json`) — pass `camera_id` on upload. Wrong-side (Tier D) is intentionally
inert: a single frame can't prove direction of travel.

**Evaluation** (`python -m eval.run [dataset.json]`) — violation-level P/R/F1, a
**rule-only vs rule+VLM ablation**, plate OCR whole/char accuracy, mean latency, and the
auto/VLM/human disposition split. Add labelled images under `data/eval/` and list them in
`eval/sample_dataset.json` (include clean images with `expected: []` to measure false
positives).

All roadmap phases (0–6) are implemented and unit-tested (29 tests).

> Helmet detection: if `HELMET_WEIGHTS` (a fine-tuned YOLO model) is set it's used;
> otherwise, if `LLM_PROVIDER=gemini`, the Gemini vision model reads helmet status per
> rider crop (no model download needed); otherwise helmet is undetermined and routes to
> VLM/human. The `.env` here already sets `LLM_PROVIDER=gemini`, so helmet detection works
> out of the box once deps are installed.
