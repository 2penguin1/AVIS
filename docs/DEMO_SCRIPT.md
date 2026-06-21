# AVIS — Demo Video Script (~3.5 min)

A tight, honest walkthrough. The thesis: **most teams claim all 7 violations from one photo;
a real camera can't, and neither can they — AVIS is the system that knows the difference.**

---

## Pre-flight checklist (do this before recording)

- [ ] `.env` set: `HELMET_WEIGHTS=models/helmet/best.pt`, `PLATE_PROVIDER=fastalpr`,
      `LLM_PROVIDER=gemini`, `GEMINI_MODEL=gemini-2.5-flash`. (Seatbelt optional: `SEATBELT_CHECK=true`.)
- [ ] `cd frontend && npm run build` (so FastAPI serves the React app at `/`).
- [ ] Start: `venv\Scripts\python.exe -m uvicorn api.main:app --reload` → open http://127.0.0.1:8000
- [ ] Have 3 images ready: **(A)** a clear motorcycle with a no-helmet rider (+plate visible),
      **(B)** a clean street photo with no violations, **(C)** a dark/blurry photo.
- [ ] Quota note: helmet + plates are **free/local**. Triple-riding & seatbelt may make ~1 Gemini
      call each — fine for a demo; just don't spam re-uploads.
- [ ] Optional: pre-run a couple uploads so Analytics has data to show.

---

## Scene 1 — Hook (0:00–0:25)

**On screen:** title card → the Violation Detectability Matrix (DESIGN.md §3).

> "Every hackathon traffic project promises to catch all seven violations from a single photo.
> Here's the uncomfortable truth: you physically can't prove wrong-side driving or a red-light
> run from one still frame — and a real enforcement camera doesn't either. So we built AVIS:
> a system that detects what it *can* prove, and is honest about what it can't."

---

## Scene 2 — The idea (0:25–1:00)

**On screen:** the architecture diagram (PROJECT_STATUS.md §2).

> "AVIS is a hybrid pipeline. Deterministic computer vision does the detecting and measuring.
> Detections become an **Evidence Graph** — riders linked to motorcycles, drivers to cars,
> plates to vehicles. Pure rules read that graph and propose violations. Each gets a **tier**:
> Tier A is provable from appearance, like no-helmet; Tier C needs camera calibration; Tier D
> needs video. A vision-language model is used **only as an auditor** to verify ambiguous cases —
> never as the detector — and it's allowed to say 'insufficient evidence'. Only Tier A can
> auto-confirm. Everything else is routed to AI verification or a human."

---

## Scene 3 — Live demo (1:00–2:40)

### 3a. A real violation (1:00–1:50)
**Action:** Analyze tab → upload image **A** (`camera_id = cam_demo`) → wait for cards.

> "I'll upload a real street photo. No model training, no cloud GPU."

**Point at the result, then open a violation card:**
> "It detected the motorcycle and rider, flagged **No Helmet**, and — this is the key part —
> it *explains itself*. Here's the **confidence breakdown**: detection, rule, and attribute
> scores fused into 0.9-something, above the auto-confirm threshold. The helmet read came from
> a **local model — zero API calls**. It cites the **law**: Motor Vehicles Act §194D, ₹1000.
> The plate was read by an on-device OCR. And there's a tamper-evident **SHA-256 evidence hash**
> and a draft **e-challan**. That's a court-ready evidence package, not a black-box verdict."

### 3b. Abstention is a feature (1:50–2:15)
**Action:** upload image **C** (dark/blurry).

> "Now a degraded photo. Instead of guessing, the quality gate makes the system **abstain** —
> 'I can't judge this fairly.' Abstaining beats a false accusation. That honesty is the whole point."

### 3c. The dashboard (2:15–2:40)
**Action:** Analytics tab → then Review queue → then Search.

> "Analytics shows violations by type, by outcome, and a **human-review-reduction** number —
> the share resolved automatically. The **review queue** is the human-in-the-loop: approve or
> reject with a note that's written to the audit trail. And every record is **searchable** by
> type, status, or plate."

---

## Scene 4 — Proof & honesty (2:40–3:05)

**On screen:** terminal with `pytest -q` (49 passed) and the eval harness file.

> "Under the hood: 49 tests, clean lint and types. The evaluation harness reports per-violation
> precision/recall/F1, a rule-only-vs-rule-plus-VLM ablation, plate accuracy, and latency — and
> it reports Tier A separately, so we never average a hard number into an easy one. We don't show
> fabricated accuracy; drop in a labelled set and the numbers are real."

*(If you have a labelled `data/eval/` set: show `python -m eval.run` output here instead.)*

---

## Scene 5 — Close (3:05–3:30)

**On screen:** the e-challan card + "free / self-hostable" line.

> "Everything runs on free, self-hostable components — one `docker compose up` brings up the API,
> worker, Postgres, Redis, and object storage. The VLM is the only external piece and it's on a
> free tier, behind a provider-agnostic client — swap in a paid model later without touching the
> pipeline. AVIS: it detects what it can prove, audits what's ambiguous, abstains on the rest, and
> explains every decision. Thanks for watching."

---

## Backup / B-roll
- Pre-recorded successful upload (in case of live network/quota hiccups).
- Screenshot of a violation detail + e-challan.
- The matrix and architecture diagrams as static slides.
