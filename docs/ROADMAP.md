# AVIS — Build Roadmap

Strategy: **vertical slice first.** Get one violation (helmet, Tier A) flowing end-to-end
— upload → detect → graph → rule → annotate → store → see it on the dashboard — before
adding breadth. A thin working pipeline beats six half-built stages at demo time. Each
phase ends with something runnable and verifiable.

Mapping to the problem statement's required tasks is noted as `[PS: …]`.

---

## Phase 0 — Skeleton (≈2h)
- FastAPI app, `POST /images` (upload) + `GET /violations` + `GET /violations/{id}`.
- `core/schemas/` Pydantic models for every stage payload (image, detection, graph,
  candidate, violation).
- SQLite via SQLModel; `storage/` abstraction (metadata + image file save/load).
- Health check + a stub pipeline that just stores the image. `pytest` green, `ruff`/`mypy` clean.
- **Verify:** upload an image via Swagger UI, see a record in SQLite.

## Phase 1 — Vertical slice: helmet end-to-end (≈5h)  `[PS: Detection, Violation Detection, Classification, Evidence]`
- Stage 3 **Detect**: Ultralytics YOLO (COCO) → person/motorcycle/etc.
- Stage 4 **Scene Graph**: rider↔motorcycle association by geometry; graph builder + tests.
- Stage 5 **Helmet** attribute (fine-tuned YOLO/classifier on rider crops).
- Stage 6 **Rule Engine**: `helmet_rule()` pure function + unit tests.
- Stage 10 **Evidence Composer**: annotated image (boxes + label) saved to filesystem.
- Minimal dashboard: upload + results table + annotated image view.
- **Verify:** upload a no-helmet image → violation row + annotated image on the dashboard.

## Phase 2 — Breadth on Tier A + plates (≈5h)  `[PS: Vehicle/Road-User Detection, License Plate Recognition]`
- Triple-riding rule (count `rides` edges) + tests.
- Vehicle classification surfaced from detector classes.
- **fast-alpr** plate detection + OCR + Indian-plate regex correction; attach plate to graph.
- **Verify:** triple-riding image flagged; plate text shown and regex-validated.

## Phase 3 — Confidence routing + VLM verification (≈5h)  `[PS: Classification + confidence scores]`
- Stage 7 **Fuse + Route**: tier-aware thresholds from config; abstain path.
- `core/llm/` provider-agnostic client → **Gemini Flash free tier**; strict JSON contract.
- Stage 8 **VLM Verify** on routed candidates; cache by `evidence_hash`; quota-safe fallback.
- Confidence + reason persisted on every violation.
- **Verify:** an ambiguous case hits the VLM and returns reason+confidence; a clear Tier-A
  case auto-confirms without a VLM call (check the cache/logs).

## Phase 4 — Tier C (calibration) + legal + robustness (≈5h)  `[PS: Preprocessing, Evidence]`
- Stage 1 **Quality gate** (blur/exposure) → `undeterminable` abstain path.
- Stage 2 **Preprocess** (CLAHE, denoise, low-light).
- Traffic-light state + per-camera calibration (`configs/`): stop-line / no-parking
  polygons via `shapely`; stop-line & illegal-parking + red-light **candidate** rules.
- Stage 9 **Legal map**: static violation→section→fine table.
- Wrong-side: low-confidence candidate only.
- **Verify:** calibrated sample image yields a stop-line candidate routed to review with
  the correct legal section; a blurry night image abstains.

## Phase 5 — Analytics, search, review queue (≈4h)  `[PS: Analytics & Reporting]`
- Dashboard: violation trends/charts (Chart.js), searchable records, summary export.
- Human-review queue UI for low-confidence/Tier-C cases (approve/reject → audit trail).
- **Verify:** stats reflect stored data; a reviewer can resolve a queued case.

## Phase 6 — Evaluation harness (≈4h)  `[PS: Performance Evaluation]`
- Scripts: component P/R/F1/mAP on public datasets; end-to-end confusion matrix +
  per-image false-positive rate; latency/throughput; auto/VLM/human split + ablation.
- **Verify:** `python -m eval.run` prints the metrics table used in the pitch.

## Phase 7 — Polish & demo (≈4h)
- One-command `docker compose up`; pre-cache VLM responses for demo images.
- 3–4 curated demo images (incl. one the system deliberately abstains on).
- Pitch deck from `docs/DESIGN.md` §14; README with screenshots.

---

## Definition of done (every phase)
`pytest -q` green · `ruff check` + `mypy` clean · the phase's **Verify** step demonstrated
with real output · no fabricated results on the demo path (stub explicitly and say so).

## Cut-scope order if time runs short
Drop in this order: optional RAG → wrong-side (Tier D) → analytics polish → seatbelt
(Tier B) → calibration (Tier C). **Never cut** the helmet/triple-riding vertical slice,
confidence routing, or the abstain path — those are the demo and the thesis.
