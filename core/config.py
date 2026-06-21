"""Central settings. Everything tunable lives here, not in literals across the code."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # storage
    database_url: str = "sqlite:///./avis.db"
    image_dir: str = "./data/images"

    # models
    detector_weights: str = "yolo11n.pt"  # ultralytics auto-downloads on first run
    detector_conf: float = 0.05
    helmet_weights: str = ""  # empty => helmet status unknown (routes to VLM/human)
    helmet_conf: float = 0.35  # confidence floor for the helmet model
    helmet_match_iou: float = 0.4  # IoU to link a helmet box to an existing rider

    # attribute checks (Tier B is quota-costly -> off by default; enable for demo)
    seatbelt_check: bool = False

    # plates
    plate_provider: str = "null"  # null | fastalpr
    plate_detector_model: str = "yolo-v9-t-384-license-plate-end2end"
    plate_ocr_model: str = "global-plates-mobile-vit-v2-model"

    # vlm
    llm_provider: str = "null"  # null | gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    # routing thresholds
    auto_confirm_threshold: float = 0.85
    review_threshold: float = 0.55

    # image quality gate
    quality_min_side: int = 64
    quality_blur_threshold: float = 8.0
    quality_dark_threshold: float = 15.0
    quality_bright_threshold: float = 245.0

    # fusion weights
    w_detection: float = 0.3
    w_rule: float = 0.4
    w_attribute: float = 0.3
    w_vlm: float = 0.4


@lru_cache
def get_settings() -> Settings:
    return Settings()
