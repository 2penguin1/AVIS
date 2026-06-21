# AVIS Documentation

Welcome to the general documentation for **AVIS (Automated Violation Intelligence System)**, codename *Gridlock*.

## 1. Project Overview

AVIS is a hybrid traffic violation detection system designed to be rigorous about evidence. Instead of claiming perfect accuracy for every type of violation from a single photo, AVIS intelligently distinguishes between:
- **Appearance Facts**: Provable from a single frame (e.g., helmet non-compliance, triple-riding).
- **Spatial Facts**: Provable using per-camera geometric calibration (e.g., stop-line violation).
- **Temporal Facts**: Usually requires motion or video, meaning a still frame only generates a "candidate" (e.g., wrong-side driving, running a red light).

By classifying violations into evidence-sufficiency tiers, AVIS provides court-ready, explainable verdicts that degrade gracefully rather than outputting false positives.

## 2. Setup and Installation

### Local Development (Zero Infrastructure)

This mode runs the entire pipeline locally using SQLite for storage and in-process execution (no Redis needed). Ideal for rapid development and testing.

```bash
# 1. Create a virtual environment
python -m venv .venv
# Activate it (Windows PowerShell)
.venv\Scripts\Activate.ps1
# (Linux/macOS) source .venv/bin/activate

# 2. Install core dependencies
pip install -r requirements.txt

# 3. Setup configuration
cp .env.example .env

# 4. Run the API server
uvicorn api.main:app --reload
```
Navigate to `http://127.0.0.1:8000` to access the API.

### Full Stack Deployment (Docker)

For production-credible environments or advanced testing with queue workers, Postgres, and MinIO:

```bash
docker compose up --build
```
This single command spins up:
- The FastAPI Backend API (`:8000`)
- PostgreSQL Database (`:5432`)
- Redis Queue (`:6379`)
- MinIO Object Storage (`:9000`, console `:9001`)

### Hugging Face Spaces Deployment (Docker)

The project includes a `Dockerfile` pre-configured to meet Hugging Face Spaces requirements (runs on port `7860`, executes as a non-root `user` with UID 1000). 

1. Create a new **Docker Space** on Hugging Face.
2. Push this repository to the Space.
3. Configure your Space secrets in the settings:
   - `GEMINI_API_KEY`: Your Gemini Flash API key.
4. The space will automatically build and deploy. Data will be stored safely in the `/home/user/app/data` directory using SQLite.

## 3. Configuration

The system is configured primarily via the `.env` file (parsed by Pydantic Settings in `core/config.py`).
Key variables include:
- `DATABASE_URL`: Connection string (defaults to `sqlite:///avis.db` for local dev).
- `LLM_PROVIDER`: `gemini` (default) or `null` to bypass VLM verification.
- `GEMINI_API_KEY`: API key for Gemini Flash.
- `PLATE_PROVIDER`: Choose `fastalpr` for license plate detection.

## 4. Testing and Evaluation

### Unit Testing
The project uses `pytest` for rigorous unit testing of rules, parsing, and pipeline flow without requiring heavy machine learning models to be loaded.
```bash
pytest -q
```

### Static Analysis
Maintain code quality with `ruff` and `mypy`.
```bash
ruff check .
mypy core/ api/
```

### ML Evaluation
To evaluate the pipeline's performance metrics (Precision, Recall, F1 score, OCR accuracy, and latency), use the dedicated evaluation script:
```bash
python -m eval.run eval/sample_dataset.json
```
This script performs a rule-only vs. rule+VLM ablation study, proving the efficacy of the hybrid approach in reducing false positives.

## 5. Development Guidelines

- **Add New Violations**: Add the violation logic as a deterministic rule function in `core/rules/` and map it to a Tier in the Rule Engine. Do not use ML models directly within the rule functions.
- **Dependency Management**: Update `requirements.txt` carefully, keeping heavy ML libraries (`ultralytics`, `fast-alpr`) separated in documentation if possible from core API dependencies.
- **Type Safety**: Pydantic schemas in `core/schemas/` are the single source of truth. Rely on the `EvidenceGraph` to pass detection data between stages.
