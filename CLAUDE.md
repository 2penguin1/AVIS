# AVIS — Automated Violation Intelligence System (codename Gridlock)

AVIS detects, classifies, and documents traffic violations from **single** traffic-camera
images. It is a **hybrid pipeline**: deterministic computer vision does the fast, reliable
detecting and measuring; a vision-language model (VLM) is used **only** to verify ambiguous
candidates, to **abstain** when a photo can't prove a violation, and to write the
human-readable justification. Output is an annotated, legally-grounded, explainable,
court-ready evidence package.

**Read first:** `docs/DESIGN.md` (full design + the Violation Detectability Matrix) and
`docs/ROADMAP.md` (phased build plan). Those are the source of truth; this file is the
working contract. Status: greenfield — the conventions below are the target to build toward.

**Cost constraint: free only.** Every component runs on open-source / self-hostable software
or a free API tier. The one external dependency is the free-tier VLM (Gemini via Google AI
Studio). Do not add a paid service or a dependency that requires billing.

## Operating principles (how I want you to work)

Act as **two senior engineers in one**:
- **An ML / computer-vision engineer**: you reason about detection vs. classification, IoU /
  bbox association, confidence calibration, false-positive cost, and P/R/F1/mAP trade-offs.
  You prefer pre-trained / zero-shot models over training and you justify model choices.
- **A senior backend engineer**: you build a clean modular monolith with crisp interfaces
  that scales out later without a rewrite; you think about latency, throughput, idempotency,
  and graceful degradation.

Mindset:
- **Explore → plan → implement.** Propose the approach for multi-file/architectural work
  before coding. If the diff fits in one sentence, just do it.
- **Reuse before you write.** Search for an existing utility/pattern first; match
  surrounding style.
- **Verify your work.** After a change, run the relevant tests / linters / type-checks and
  show the evidence. Never report success you haven't checked.
- **Address root causes, not symptoms.** Don't suppress errors to make a check pass.
- **Be honest over impressive.** Never fabricate accuracy or demo results. Abstaining or
  reporting low confidence is correct behaviour, not failure.

## Architecture — invariants (do not violate)

A **production-credible modular monolith**: one FastAPI codebase. The API enqueues work to a
**Redis-backed worker** that runs the pipeline (in-process fallback for quick local dev).
Stages communicate via Pydantic payloads through clean interfaces. Horizontally scalable by
adding workers — without splitting into many microservices.

```
upload → 1 Ingest+QualityGate → 2 Preprocess → 3 Detect → 4 SceneGraph
       → 5 Attributes(helmet/seatbelt/plate) → 6 RuleEngine → 7 Fuse+Route
       → 8 VLM Verify (only when routed) → 9 Legal map → 10 Evidence Composer → store
```

- **IMPORTANT: the VLM is an *auditor*, never the primary detector.** Detection is done by
  deterministic CV models. The VLM only answers "does this crop support this candidate?"
  and may return `insufficient_evidence`. Never put a VLM call on the detection path.
- **IMPORTANT: evidence sufficiency is mandatory.** Every violation carries a **tier**
  (A appearance / B hard-appearance / C spatial-needs-calibration / D temporal) and an
  evidence-sufficiency level. **Only Tier A may auto-confirm.** Tiers B/C/D produce
  *candidates* routed to VLM or human review — never auto-confirmed. See the matrix in
  `docs/DESIGN.md §3`.
- **Abstain over guess.** If the quality gate fails or the VLM is unsure, output
  `undeterminable` — not a false positive.
- **The Evidence Graph is the single source of truth.** Detections become a typed graph
  (riders↔motorcycles, drivers↔cars, plates, lights, zones). All rules and reasoning read
  the graph, not raw boxes.
- **The Rule Engine is deterministic and pure.** It consumes the graph + optional per-camera
  calibration and emits candidates with a rule-evidence score. No ML, no I/O, no randomness
  — fully unit-testable. One violation = one pure function in `core/rules/`.
- **Confidence routing is mandatory and config-driven.** Fuse detection/attribute/rule
  (+VLM) scores; route by tier-aware thresholds (auto-confirm / VLM / human / abstain).
- **Every output is explainable:** reason + confidence + tier + legal reference (act /
  section / fine) + SHA-256 evidence hash + audit trail. No black-box verdicts.
- **Respect the free VLM quota** (~1,500/day, ~10/min): route sparingly, **cache by
  `evidence_hash`**, degrade to human review when exhausted.

Supported violations (v1): helmet, triple riding (Tier A); seatbelt (B); stop-line,
red-light, illegal parking (C, candidate); wrong-side (D, candidate). Plate OCR supports all.

## Tech stack (MVP — build this)

- **Python 3.11** · FastAPI · Uvicorn · **Redis-backed worker** (Celery or RQ/ARQ) for heavy
  CV; in-process fallback for quick local dev
- **Detection:** Ultralytics **YOLO11/YOLOv8** (pretrained COCO + fine-tuned helmet/plate
  from Roboflow). *Grounding DINO / YOLO-World are optional enhancements — slow & painful to
  install; do not make them a dependency.*
- **Plates:** **fast-alpr** (`fast-plate-ocr`, ONNX, CPU-fast) + Indian-plate regex correction
- **VLM (verify + seatbelt/ambiguous):** **Gemini Flash free tier** behind a
  provider-agnostic client in `core/llm/` (swappable for Groq / OpenRouter free models)
- **Storage:** **Postgres (JSONB)** via SQLModel for metadata *and* the evidence graph;
  **MinIO** (free, S3-compatible) for images — both behind a `core/storage/` abstraction
- **Legal:** static violation→section→fine table (optional ChromaDB RAG is a *bonus*, never
  load-bearing)
- **CV utils:** OpenCV (preprocess + annotate), `shapely` (zone polygons)
- **Frontend:** React + Vite + Chart.js
- **Packaging:** one `docker compose up` brings up api + worker + Postgres + Redis + MinIO

> **Scale-out path (documented in `docs/DESIGN.md §13`, do NOT build now):** add more workers;
> swap MinIO→S3 and Postgres→managed; run detection as GPU workers; optionally peel stages
> into microservices. Because stages talk through `storage/` and `llm/` interfaces, this is a
> deployment change, not a rewrite. Full microservices are deliberately avoided for the MVP.

## Project layout (where code goes)

```
api/                FastAPI app — routes only (upload, violations, analytics). No ML here.
core/
  pipeline/         the 10 stages + the orchestrator that chains them
  schemas/          Pydantic models for every stage payload
  graph/            Evidence-Graph builder + types (single source of truth)
  rules/            one pure function per violation type
  detect/           YOLO wrappers + attribute classifiers (helmet, light-state)
  plates/           fast-alpr wrapper + Indian-plate regex
  llm/              provider-agnostic VLM client (model selection lives here)
  legal/            static violation→law table (+ optional rag/)
  queue/            Redis worker + task enqueue (in-process fallback for local dev)
  storage/          Postgres (JSONB) + MinIO access (the ONLY place that touches them)
  evidence/         annotated-image composer + hashing/audit
configs/            per-camera calibration JSON (stop lines, lanes, no-parking zones)
frontend/           React + Vite dashboard
eval/               evaluation harness (metrics, confusion matrix, ablation)
tests/              pytest — unit (rules, graph, regex) + integration (E2E)
data/               sample images + (optional) legal corpus (gitignore if large)
docs/               DESIGN.md, ROADMAP.md, PROJECT_STATUS.md, DEMO_SCRIPT.md
```

Never call models or datastores directly from `api/`; go through `core/`.

## Commands

> The repo is new — create these as you scaffold and keep this section accurate.

```bash
# Setup
python -m venv .venv && .venv\Scripts\activate     # PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env                               # set GEMINI_API_KEY (free)

# Build the dashboard (FastAPI serves frontend/dist at / once built)
cd frontend && npm install && npm run build && cd ..

# Run
docker compose up --build                          # full stack: api + worker + postgres + redis + minio
uvicorn api.main:app --reload                      # API + built dashboard (in-process task fallback)
celery -A core.queue.app worker -l info            # background worker (skip in in-process mode)
cd frontend && npm run dev                          # dashboard hot-reload (proxies API to :8000)

# Quality gates — run before saying a task is done
pytest -q                                          # prefer a single test file while iterating
ruff check . && ruff format --check .              # lint + format
mypy core/ api/                                     # type-check
python -m eval.run                                  # metrics table (needs labelled data/eval/ images)
```

> Local helmet model ships at `models/helmet/best.pt` (set `HELMET_WEIGHTS`) → helmet
> detection runs offline with **zero API calls**. Plate OCR needs `onnxruntime` (in
> requirements). See `docs/PROJECT_STATUS.md` for live status, task board, and the change log.

## Code style & conventions (only what differs from defaults)

- **Type hints mandatory** on every signature; code must pass `mypy`.
- **Pydantic models** for all inter-stage payloads — never pass raw dicts between stages.
- Formatting/lint: **ruff** (88-col). `snake_case` funcs/vars, `PascalCase` classes.
- **Config over hardcoding:** thresholds, model names, routing cut-offs, calibration come
  from config/env — never literals buried in code.
- **Money & law are strings/enums**, never floats (e.g. `"₹1000"`).
- **Logging, not prints.** Never log full images or secrets — log IDs, scores, decisions.
- Docstrings on public functions: purpose, params, returns, raised exceptions.

## Testing

- **Rule Engine first** — it's pure, so unit tests with mock graphs + camera configs are
  cheap and high-value. Also unit-test the graph builder (rider↔vehicle linking) and the
  plate-OCR regex.
- **Integration** — upload a known image via the API, assert the stored violation matches:
  a clear Tier-A violation, a clean (no-violation) image, a degraded image (expect
  `undeterminable`), and a corrupt upload (expect 4xx).
- **Eval harness** — per-violation P/R/F1 (IoU-matched), plate OCR accuracy, latency,
  auto/VLM/human split, and the rule-only-vs-rule+VLM ablation. Report Tier A separately
  from C/D — never average them into one inflated number.
- Mock the VLM/external calls in unit tests; only the integration suite may hit them.

## Common gotchas

- Triple riding is geometric (count `rides` edges); seatbelt is genuinely unreliable from
  traffic cams (Tier B) — route it, don't trust it.
- Tier C/D need per-camera calibration; without it, route to human review, don't fabricate.
- Indian plate OCR needs regex post-processing (`^[A-Z]{2}[0-9]{1,2}[A-Z]{1,2}[0-9]{4}$`).
- Gemini free tier is rate-limited; cache by `evidence_hash` and degrade gracefully.
- Keep the original image untouched for evidence; annotate a copy.

## Out of scope (v1) — don't build unprompted

Video/temporal tracking, model fine-tuning/training, real e-challan/government API
integration, blockchain, multi-camera fusion. Note them as future scope; don't build them.

## Working agreements

- Don't commit, push, or create branches unless I ask.
- Don't add a dependency without flagging it; prefer what's already in the stack.
- When you finish a unit of work, show the command output that proves it works.
- Hackathon bias: a working end-to-end vertical slice beats six half-built stages — follow
  the slice order in `docs/ROADMAP.md`. Never fake results on the demo path; stub explicitly
  and say so.
