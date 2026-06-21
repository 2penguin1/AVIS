"""Provider-agnostic VLM client. The VLM is an *auditor*: it verifies a proposed
violation crop or abstains. Swapping Gemini (free) -> Claude/GPT-4o later is a config
change here, with no call-site edits.

Contract returned by ``verify``:
    {
      "verified": bool,
      "confidence": float,
      "reason": str,
      "insufficient_evidence": bool,
      "verifier_unavailable": bool,
    }
"""

from __future__ import annotations

import json
import sys
import time
from collections.abc import Callable
from typing import Protocol

from core.config import Settings, get_settings

_PROMPT = (
    "You are a traffic-enforcement auditor. Given the image and a PROPOSED violation, "
    "decide ONLY whether the visible evidence supports it. Don't add new ones. "
    "If the image is too unclear to judge, set insufficient_evidence=true.\n"
    "Proposed violation: {vtype}\nEvidence note: {reason}\n"
    'Reply with ONLY JSON: {{"verified": bool, "confidence": 0.0-1.0, '
    '"reason": "<one sentence>", "insufficient_evidence": bool}}'
)

_UNAVAILABLE = {
    "verified": False,
    "confidence": 0.0,
    "reason": "VLM unavailable or could not judge the evidence.",
    "insufficient_evidence": False,
    "verifier_unavailable": True,
}


def call_with_retry(fn: Callable, attempts: int = 3, base_delay: float = 2.0):
    """Run ``fn``; retry transient API errors (e.g. 429) with linear backoff."""
    last: Exception | None = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            last = e
            if i < attempts - 1:
                time.sleep(base_delay * (i + 1))
    raise last  # type: ignore[misc]


class LLMClient(Protocol):
    enabled: bool

    def verify(self, image_path: str, vtype: str, reason: str) -> dict: ...


class NullLLM:
    """No VLM configured. Disabled -> the pipeline escalates to human review."""

    enabled = False

    def verify(self, image_path: str, vtype: str, reason: str) -> dict:
        return dict(_UNAVAILABLE)


class GeminiLLM:
    """Wraps the current ``google-genai`` SDK. Crops/images are sent as JPEG bytes."""

    enabled = True

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model_name = model
        self._client = None

    def _client_obj(self):  # noqa: ANN202
        if self._client is None:
            from google import genai

            self._client = genai.Client(api_key=self._api_key)
        return self._client

    def verify(self, image_path: str, vtype: str, reason: str) -> dict:
        try:
            from io import BytesIO

            from google.genai import types
            from PIL import Image

            buf = BytesIO()
            Image.open(image_path).convert("RGB").save(buf, format="JPEG")
            prompt = _PROMPT.format(vtype=vtype, reason=reason)
            resp = call_with_retry(
                lambda: self._client_obj().models.generate_content(
                    model=self._model_name,
                    contents=[
                        prompt,
                        types.Part.from_bytes(
                            data=buf.getvalue(), mime_type="image/jpeg"
                        ),
                    ],
                )
            )
            text = (resp.text or "").strip().removeprefix("```json").removeprefix("```")
            text = text.removesuffix("```").strip()
            data = json.loads(text)
            return {
                "verified": bool(data.get("verified", False)),
                "confidence": float(data.get("confidence", 0.0)),
                "reason": str(data.get("reason", "")),
                "insufficient_evidence": bool(data.get("insufficient_evidence", False)),
                "verifier_unavailable": False,
            }
        except Exception as e:  # noqa: BLE001
            print(f"[gemini.verify] {type(e).__name__}: {e}", file=sys.stderr)
            return dict(_UNAVAILABLE)


def get_llm(settings: Settings | None = None) -> LLMClient:
    settings = settings or get_settings()
    if settings.llm_provider == "gemini" and settings.gemini_api_key:
        return GeminiLLM(settings.gemini_api_key, settings.gemini_model)
    return NullLLM()
