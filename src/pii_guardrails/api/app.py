"""FastAPI application factory.

Wires the reusable GuardrailService (with the OpenAI detector by default) into the
two routes. A pre-built service can be injected (used by tests to substitute a fake
detector), demonstrating the swappable-detector design.
"""

from __future__ import annotations

from fastapi import FastAPI

from ..core.config import Settings, get_settings
from ..core.logging import configure_logging
from ..detectors.openai_detector import OpenAIDetector
from ..service import GuardrailService
from .routes import register_exception_handlers, router


def build_default_service(settings: Settings | None = None) -> GuardrailService:
    settings = settings or get_settings()
    detector = OpenAIDetector(settings=settings)
    return GuardrailService(detector=detector, max_payload_bytes=settings.max_payload_bytes)


def create_app(service: GuardrailService | None = None) -> FastAPI:
    configure_logging()
    app = FastAPI(
        title="PII Guardrails",
        version="0.1.0",
        description="Two APIs: PII Detection and PII Redaction.",
    )
    app.state.service = service or build_default_service()
    app.include_router(router)
    register_exception_handlers(app)
    return app


# Module-level app for `uvicorn pii_guardrails.api.app:app`.
# The OpenAI client is created lazily on first use, so the app boots without a key;
# detection calls fail closed at request time if the key is missing.
app = create_app()
