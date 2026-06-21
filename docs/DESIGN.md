# AVIS — Automated Violation Intelligence System
### Design & Concept Note · codename *Gridlock*

> **Thesis.** Most teams will claim they detect all seven violations at high accuracy from a
> single photo. That claim is false, and judges who know vision will see through it. AVIS
> wins by being the system that is *rigorous about evidence*: it detects what a photograph
> can actually prove, attaches an explicit **evidence-sufficiency level** and confidence to
> every finding, uses a vision-language model to verify ambiguous cases and to **abstain**
> when the image doesn't support a verdict, and emits a court-ready, explainable evidence
> package. Honesty + explainability + human-in-the-loop is the differentiator.

This document is the single source of truth for the project's objective and design. It
replaces the earlier draft (`context.md`), which over-engineered the infrastructure and
over-claimed what is detectable from one image.

---

## 1. Problem & what makes it genuinely hard

Traffic cameras produce huge volumes of images; manual review is slow, inconsistent, and
expensive. The task: automatically detect road users, identify and classify violations,
recognise plates, and generate annotated evidence — robust to low light, rain, shadows,
motion blur, density, and image quality.

The non-obvious difficulty — and the thing the original plan glossed over — is that
**violations differ enormously in how provable they are from a single still image:**

- Some are **appearance facts** visible in one frame (no helmet, three people on a bike).
- Some are **spatial facts** that need to know the scene geometry (a vehicle past the
  stop line) — solvable from one image *only with per-camera calibration*.
- Some are **temporal/behavioural facts** (running a red light, driving the wrong way,
  *parking* = staying put) that fundamentally require motion or duration. Real red-light
  cameras use video buffers and multiple angles and *still* misfire on cars that brake
  hard at the line. A single photo can produce a *candidate*, never proof.

A credible system must encode this distinction instead of pretending it doesn't exist.

---

## 2. Design philosophy (the objective, reframed)

1. **Evidence sufficiency first.** Every violation type is tagged with what evidence a
   single image can provide. The system never auto-confirms a violation the photo can't
   prove — it produces a *candidate* and routes it for verification or human review.
2. **Deterministic CV for detection; AI for judgement.** Fast, reliable open models do the
   detecting and measuring. A vision-language model (VLM) is used **only** to verify
   ambiguous candidates, to abstain when evidence is weak, and to write the human-readable
   justification. This keeps the pipeline cheap, fast, and explainable.
3. **Explainable & accountable by construction.** Every output carries: the reason, the
   confidence, the evidence-sufficiency level, the legal reference, and a tamper-evident
   hash. No black-box verdicts; a human can always be put in the loop.
4. **Right-sized engineering.** A clean modular monolith that runs on a laptop/CPU and free
   APIs — with a clearly documented path to horizontal scale. We spend our time on the CV
   and the demo, not on orchestration plumbing.
5. **Free and self-hostable.** Open-source models + one free API tier (Gemini). No billing.

---

## 3. The Violation Detectability Matrix  *(the core intellectual contribution)*

Each violation is assigned a **tier** that determines its evidence-sufficiency level and
how the pipeline routes it. This table drives the Rule Engine and the routing policy.

| Violation | Tier | What a single image proves | Inputs needed | Default route |
|---|---|---|---|---|
| **Helmet non-compliance** | **A — Appearance** | Reliable: rider head visible, helmet/no-helmet | Detector + helmet classifier | Auto-confirm if high conf, else VLM |
| **Triple riding** | **A — Appearance** | Reliable: count riders linked to one motorcycle | Detector + rider↔bike association | Auto-confirm if clean count, else VLM |
| **Seatbelt non-compliance** | **B — Hard appearance** | Weak: windshield glare/resolution make this unreliable | Windshield crop classifier *or* VLM | VLM-verify or human; mark low-confidence |
| **Stop-line violation** | **C — Spatial (needs calibration)** | Strong *candidate*: vehicle body past the stop-line zone | Detector + per-camera stop-line polygon | VLM-verify; human if no calibration |
| **Red-light violation** | **C/D — Spatial + temporal** | Candidate only: light=red (from image) AND vehicle past stop line; true running is temporal | Detector + light-state + stop-line polygon | Always VLM-verify + flag "confirm with sequence" |
| **Illegal parking** | **C/D — Spatial + temporal** | Candidate only: vehicle inside no-parking zone; "parked" = duration, unprovable from one frame | Detector + no-parking polygon | Candidate; flag "needs dwell-time confirmation" |
| **Wrong-side driving** | **D — Temporal** | Not provable: direction of travel needs motion; orientation-vs-lane is a weak proxy | Detector + lane direction (+ orientation) | Low-confidence candidate; recommend video |
| **License-plate recognition** | *(supporting)* | Reliable when plate is legible | Plate detector + OCR + regex | Always attempted; attach to any violation |

**Consequence for the build:** Tier A is our headline, demo-grade capability. Tier B is
best-effort with honest confidence. Tiers C/D are positioned as **candidate generation +
calibration-assisted evidence**, never as "we solved red-light running from a JPEG." This
framing is defensible and impressive; over-claiming is not.

---

## 4. System overview

A **production-credible modular monolith**: one FastAPI codebase running a linear pipeline of
pure-ish stages, with the heavy CV work handed to a **worker via a Redis queue** so the API
stays responsive. This is production-grade *and* demo-safe — real horizontal scalability (add
workers) without splitting into many microservices. Everything is free/self-hosted and comes
up with one `docker compose up`. Storage and the queue sit behind interfaces, so a developer
can run a lightweight local mode (in-process tasks + filesystem) when they don't want to
start the full stack.

```
  upload → FastAPI api ──enqueue──▶ Redis ──▶ Worker(s): pipeline stages 1–10
                                                  │
   1 Ingest+QualityGate → 2 Preprocess → 3 Detect → 4 SceneGraph
   → 5 Attributes(helmet/seatbelt/plate) → 6 RuleEngine → 7 Fuse+Route
   → 8 VLM Verify (Gemini, only when routed) → 9 Legal map → 10 Evidence Composer
                                                  │
        ┌──────────────────────────────────────┴─────────────────────────────┐
  Postgres (JSONB: metadata + evidence graph)                  MinIO (S3: images)
        └──────────────────────────────────────┬─────────────────────────────┘
                                                ▼
                                  React + Vite dashboard
                        (upload · review queue · analytics · search)
   scale: add workers · swap MinIO→S3, Postgres→managed · GPU detection workers
```

### Stage responsibilities
1. **Ingest + Quality Gate** — store the image + metadata (camera_id, timestamp, geo if
   given); run a blur/exposure/resolution check. If the image is unusable, mark
   `undeterminable` and stop — *abstaining is a feature, not a failure.*
2. **Preprocess** — OpenCV: CLAHE (contrast), denoise, optional low-light enhancement
   (gamma / Retinex-style), light deblur. Produces a normalised image; keeps the original
   untouched for evidence.
3. **Detect** — YOLO11/YOLOv8 (COCO) for car/truck/bus/motorcycle/bicycle/person/traffic
   light; a fine-tuned model adds helmet and plate classes. Output: boxes + class + conf.
4. **Scene Graph** — associate people to vehicles by geometry (rider↔motorcycle,
   driver↔car), attach traffic lights and plates. This graph is the single source of truth
   for all downstream reasoning (§5).
5. **Attribute classifiers** — helmet per rider (YOLO/classifier); seatbelt per driver
   (windshield crop classifier or VLM, Tier B); traffic-light state (HSV + classifier);
   plate text (fast-alpr OCR + Indian-plate regex correction).
6. **Rule Engine** — pure, deterministic functions, one per violation, consuming the graph
   + optional per-camera calibration. Emits **candidates** with a rule-evidence score and
   the tier from §3. No ML, no I/O — fully unit-testable.
7. **Fuse + Route** — combine detection / attribute / rule scores into a fused confidence;
   apply tier-aware routing (§7): auto-confirm, VLM-verify, human-review, or abstain.
8. **VLM Verify** — only for routed candidates: send the cropped evidence + a strict prompt
   to **Gemini Flash (free tier)**; get `{verified, confidence, reason}` or
   `insufficient_evidence`. Sparingly used to respect the 1,500/day, ~10/min free quota.
9. **Legal map** — deterministic lookup table: violation → Motor Vehicles Act section →
   fine. (Correct, instant, free. Optional RAG is a bonus feature, not load-bearing — §10.)
10. **Evidence Composer** — annotated image (boxes, labels, plate, reason) + structured
    JSON + SHA-256 hash + audit trail; persist to Postgres (JSONB) + MinIO.

---

## 5. The Evidence Graph (data model)

Detections become a typed graph, not a flat list. This is what makes the system queryable,
explainable, and auditable.

```
Nodes:
  Vehicle  { id, type, bbox, conf, attrs:{orientation?, in_zones:[...]} }
  Person   { id, role: rider|driver|pedestrian, bbox, conf, attrs:{helmet?, seatbelt?} }
  Light    { id, state: red|amber|green|unknown, bbox, conf }
  Plate    { id, text, regex_ok, conf, bbox }
  Zone     { id, kind: stop_line|no_parking|lane, polygon }      # from camera calibration

Edges:
  rides(Person → Vehicle:motorcycle)      drives(Person → Vehicle:car)
  has_plate(Vehicle → Plate)              located_in(Vehicle → Zone)
  governed_by(Vehicle → Light)
```

A violation is then a small, explainable subgraph, e.g. *triple riding* =
`motorcycle_1` with three `rides` edges. "Why?" is answerable directly from the graph
(*"3 riders linked to 1 motorcycle"*). Example output payload:

```json
{
  "violation": "TRIPLE_RIDING",
  "tier": "A",
  "evidence_sufficiency": "sufficient",
  "subjects": ["motorcycle_1", "rider_1", "rider_2", "rider_3"],
  "scores": { "detection": 0.94, "rule": 0.90, "vlm": 0.93, "fused": 0.92 },
  "route": "auto_confirmed",
  "reason": "Three distinct riders are linked to a single motorcycle.",
  "plate": { "text": "UP32AB1234", "regex_ok": true, "conf": 0.88 },
  "legal": { "act": "Motor Vehicles Act, 1988", "section": "128", "fine": "₹1000" },
  "evidence_hash": "sha256:…",
  "timestamp": "2026-06-20T10:31:00Z"
}
```

---

## 6. Confidence fusion & routing (with abstention)

Per candidate, fuse available signals with tier-specific weights:

```
fused = w_det·detection_conf + w_attr·attribute_conf + w_rule·rule_evidence (+ w_vlm·vlm_conf)
```

Routing policy (thresholds are config, not hardcoded):

- **Tier A:** `fused ≥ 0.85` and unambiguous → **auto-confirm**; `0.55–0.85` → **VLM-verify**;
  `< 0.55` → **human review**.
- **Tier B (seatbelt):** never auto-confirm → **VLM-verify**, then human if VLM is unsure.
- **Tier C (stop-line / red-light / parking):** never auto-confirm. With calibration →
  **VLM-verify** and label `candidate`; without calibration → **human review**.
- **Tier D (wrong-side):** emit **low-confidence candidate** + "recommend video
  confirmation"; never auto-confirm.
- **Quality gate failed or VLM returns `insufficient_evidence`** → **abstain**
  (`undeterminable`), not a false positive.

This is what makes the free Gemini quota workable: only the genuinely ambiguous minority
hits the VLM, and clear Tier-A cases auto-confirm for free.

---

## 7. VLM verification layer (Gemini free tier)

- **Role:** auditor, never detector. It receives a *focused crop* + the proposed violation
  + the graph evidence, and answers a strict JSON contract:
  ```
  {"verified": bool, "confidence": 0.0-1.0, "reason": "<one sentence>",
   "insufficient_evidence": bool}
  ```
- **Model:** Gemini Flash (free tier) via a provider-agnostic client so it can swap to
  Groq / OpenRouter free models without touching call sites.
- **Budget discipline:** free tier = ~1,500 req/day, ~10/min. Therefore: route sparingly,
  batch where possible, **cache by `evidence_hash`** (identical crops never re-billed),
  and degrade gracefully to "human review" if the quota is exhausted. For the live demo,
  pre-cache responses for the demo images.

---

## 8. Legal grounding

For seven fixed violation types, the violation→section→fine mapping is a **small static
table** — correct, instant, and free. That table is the source of truth.

*Optional wow-factor (only if time allows):* a tiny RAG layer (ChromaDB +
sentence-transformers over the Motor Vehicles Act text) that lets an officer **ask
free-form questions** ("what's the penalty for X, and the appeal process?"). This is a
bonus feature layered on top — it must never be on the critical path of issuing a verdict.

---

## 9. Evidence package (court-ready output)

Each confirmed/escalated violation produces:
- **Annotated image** — original (untouched) + an overlay copy with boxes, labels,
  plate, and the natural-language reason.
- **Structured JSON** — the payload in §5, including scores, tier, route, legal ref.
- **Integrity** — SHA-256 hash of the original image + an append-only audit trail
  (who/what changed the verdict, when). This is the "admissible evidence" story.
- **e-challan-ready** — plate + violation + section + fine in one record, exportable.

---

## 10. Robustness to varying conditions (explicitly required)

- **Preprocessing** handles low light (CLAHE / gamma / Retinex), rain & noise (denoise),
  motion blur (mild deblur / sharpening).
- **Quality gate** quantifies blur/exposure and *abstains* on images too poor to judge —
  preventing confident-but-wrong outputs, which is the real failure mode under bad
  conditions.
- **VLM second opinion** adds robustness on ambiguous/degraded crops and can abstain.
- **Honest confidence** means degraded inputs surface as lower confidence → review, not as
  silent false positives.

---

## 11. Why this wins (innovation summary)

1. **Evidence-sufficiency–aware detection** — explicit tiers + abstention. Rigorous and
   rare; directly answers "robust and accurate" without over-claiming.
2. **Evidence Graph** — relationship-first, explainable single source of truth.
3. **VLM-as-verifier-and-abstainer** — cuts false positives, writes human-readable reasons,
   stays inside a free quota by only judging the hard cases.
4. **Confidence routing with human-in-the-loop** — quantifiable "human-review reduction %".
5. **Court-ready evidence** — legal grounding + tamper-evident hash + audit trail.
6. **Calibration-optional** — works on arbitrary images for Tier A; uses optional per-camera
   zones for Tier C; clearly degrades elsewhere.

---

## 12. Evaluation plan (mapped to the required metrics)

- **Component metrics (P / R / F1 / mAP):** on public datasets — helmet & triple-riding
  (Roboflow), plate detection + OCR character/whole-plate accuracy. Report per class.
- **End-to-end:** a hand-curated ~60–100 image set spanning day/night/rain/density, with a
  per-violation confusion matrix and false-positive rate **per image** (the metric that
  actually governs reviewer workload).
- **Operational:** mean latency/image on CPU, throughput (images/min), and the
  **auto-confirm vs. VLM vs. human** split → human-review-reduction %.
- **Ablation (great for judges):** rule-only vs. rule+VLM, to quantify the false-positive
  reduction the VLM buys.
- **Honesty:** report Tier A separately from C/D; never average them into one inflated
  "accuracy" number.

---

## 13. Tech stack (free) & scalability path

**MVP (build this) — a production-credible monolith, all free/self-hosted:**
- Python 3.11 · FastAPI · Uvicorn · **Redis-backed worker queue** (Celery or RQ/ARQ) so the
  API stays responsive and scales by adding workers; in-process fallback for quick local dev.
- **Detection:** Ultralytics **YOLO11/YOLOv8** (pip, pretrained COCO + fine-tuned
  helmet/plate from Roboflow). *(Open-vocab Grounding DINO / YOLO-World is an optional
  enhancement, not a dependency — it's slow and painful to install.)*
- **Plates:** **fast-alpr** (detection + `fast-plate-ocr`, ONNX, CPU-fast) + Indian-plate
  regex correction.
- **Seatbelt/ambiguous:** Gemini VLM (Tier B/C).
- **VLM:** **Gemini Flash free tier** via provider-agnostic `core/llm/` client — a one-line
  swap to a paid model (Claude / GPT-4o) later, with zero code rework. Free is a demo-time
  choice, not a capability ceiling.
- **Storage:** **Postgres (JSONB)** via SQLModel for metadata *and* the evidence graph
  (relational integrity + native JSON querying); **MinIO** (free, S3-compatible) for images.
  Both behind a `core/storage/` abstraction.
- **Legal:** static lookup table (+ optional ChromaDB RAG bonus).
- **Frontend:** React + Vite + Chart.js.
- **Packaging:** one `docker compose up` brings up api + worker + Postgres + Redis + MinIO.

**Why not full microservices?** This monolith already delivers the real scalability win — a
true task queue and horizontally-scalable workers — in one maintainable codebase. Splitting
the stages into separately-deployed services adds ops burden and demo risk for little extra
scalability during a hackathon.

**Scale-out path (a deployment change, not a rewrite):** add more workers; swap MinIO → AWS
S3 and Postgres → a managed instance; run the detection stage as dedicated GPU workers; and,
if ever truly needed, peel stages into separate services behind the same `storage/` and
`llm/` interfaces. Because everything already talks through those interfaces, none of this
touches business logic.

---

## 14. Pitch & demo flow (3–4 min)

1. **Hook (20s):** "Every team says they catch all 7 violations from a photo. They can't —
   and neither can a real red-light camera from one frame. We built the system that knows
   the difference."
2. **Idea (40s):** hybrid CV + VLM, Evidence Graph, evidence-sufficiency tiers, routing.
3. **Live demo (90s):** upload a triple-riding image → annotated result, graph panel
   ("motorcycle → 3 riders, 1 helmet"), VLM reason, plate OCR, legal section + fine; then a
   degraded night image → system **abstains / routes to review** (show this on purpose);
   then the analytics + review-queue dashboard.
4. **Proof (30s):** metrics table (Tier A P/R/F1, ablation showing VLM cuts false positives,
   human-review-reduction %).
5. **Close (20s):** free/self-hostable, calibration-optional, scale-out path, e-challan-ready.

---

## 15. Risks & honest limitations

| Risk | Mitigation |
|---|---|
| Seatbelt detection unreliable | Tier B: best-effort + VLM/human; report honest confidence |
| Tier C/D need calibration we won't have for random images | Position as candidate generation; demo with one calibrated camera config |
| Free Gemini quota exhausted | Cache by hash, route sparingly, pre-cache demo, degrade to human review |
| Grounding DINO install eats hackathon time | Default to Ultralytics YOLO; open-vocab is optional |
| Public model accuracy varies on Indian scenes | Pick India-trained Roboflow models; report measured, not claimed, numbers |

---

## References
- Gemini API free tier limits (2026): https://tokenmix.ai/blog/gemini-api-free-tier-limits
- fast-alpr / fast-plate-ocr: https://github.com/ankandrew/fast-alpr
- Triple-riding + helmet via YOLOv8 (CCTV): https://www.atlantis-press.com/proceedings/computatia-25/126010076
- Helmet violation detection, Indian smart-city (YOLOv8/TAO): https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2025.1582257/full
- Red-light running needs video (false positives from braking): https://www.researchgate.net/publication/3154744_An_effective_video_analysis_method_for_detecting_red_light_runners
- VLM on complex traffic events (GPT-4V study): https://arxiv.org/pdf/2402.02205
