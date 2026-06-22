# File Structure Documentation

The AVIS project is organized as a modular monolith. This document outlines the purpose of each directory and significant files.

## Root Directory

```text
AVIS/
├── .env.example         # Template for environment variables
├── docker-compose.yml   # Orchestration for full-stack deployment
├── Dockerfile           # Docker container definition for the API
├── pyproject.toml       # Project metadata and tool configuration (Ruff, Mypy)
├── requirements.txt     # Python package dependencies
├── README.md            # Quickstart guide
└── Devdocs/             # Comprehensive system documentation
```

## `api/` (Presentation Layer)
Contains the FastAPI application entry point and route definitions.
- `main.py`: Bootstraps the FastAPI app, wires up dependencies, and defines HTTP endpoints (e.g., `POST /images`, `GET /status`).

## `core/` (Domain & Business Logic)
The heart of the application, broken down into specific bounded contexts.

- `config.py`: Pydantic settings loading the `.env` file configurations.
- `schemas/`: Contains the Pydantic models acting as the data contract.
  - `__init__.py`: Defines `EvidenceGraph`, `Detection`, `Zone`, `Candidate`, `Violation`, etc.
- `pipeline/`: The orchestrator for the 10-stage processing workflow. Passes data sequentially through the stages.
- `preprocess/`: OpenCV-based image enhancement (CLAHE, denoise, deblur).
- `detect/`: Wrappers for Ultralytics YOLOv8/11.
- `graph/`: Logic for associating raw detections into semantic relationships (e.g., calculating Intersection over Union to link riders to a motorcycle).
- `rules/`: Pure, deterministic functions that evaluate the Evidence Graph against predefined violation criteria.
- `llm/`: Provider-agnostic wrappers for interacting with Vision-Language Models (primarily Google Gemini).
- `plates/`: Integration with `fast-alpr` for OCR and regex validation of license plates.
- `legal/`: Static mappings that tie specific violations to the Motor Vehicles Act sections and fine amounts.
- `quality/`: The initial "Quality Gate" that analyzes exposure and blur to abstain from processing unusable images.
- `storage/`: Abstracted interfaces for saving structured data (Postgres via SQLModel) and blobs (MinIO/S3).
- `queue/`: Wrappers for the Redis background task queue.

## `frontend/` (User Interface)
The React + Vite single-page application for the dashboard.
- `package.json`: NPM dependencies including React, Vite, React Router, and Chart.js.
- `src/`: React components for image upload, reviewing the human-in-the-loop queue, and displaying analytics charts.
- `vite.config.js`: Vite build configuration.

## `configs/` (Deployment specific)
Contains JSON camera calibration files.
- e.g., `cam_demo.json`: Defines geometric polygons (`stop_line`, `no_parking`, `lane` vectors) specific to a single camera's field of view, critical for Tier C/D violations.

## `data/` and `models/` (Assets)
- `data/`: Local storage directory (if not using MinIO) and labeled datasets for evaluation.
- `models/`: Directory to cache downloaded YOLO `.pt` weights and ONNX models to avoid redownloading.

## `docs/` (Original Specs)
Original foundational specifications for the project.
- `DESIGN.md`: The single source of truth for the architectural philosophy, evidence tiers, and routing logic.
- `ROADMAP.md`: Outlines the phased implementation plan.

## `eval/` (Evaluation Suite)
Scripts for measuring the performance of the pipeline.
- `run.py`: Executes the ablation study and calculates P/R/F1 scores.
- `sample_dataset.json`: Metadata linking test images to expected ground-truth violations.

## `tests/` (Test Suite)
- Contains unit tests (via Pytest) focused on the deterministic logic (Graph association, Rule Engine, Legal mappings) ensuring core business logic is sound without requiring heavy ML inference.
