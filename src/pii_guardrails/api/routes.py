"""The two primary API routes: /v1/detect and /v1/redact, plus a health check."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from ..core.errors import DetectionUnavailableError
from ..core.logging import get_logger, safe_extra
from ..redaction.engine import RedactionOptions
from ..service import GuardrailService
from .schemas import (
    ActionSummary,
    DetectedEntity,
    DetectRequest,
    DetectResponse,
    RedactRequest,
    RedactResponse,
)

logger = get_logger("api")
router = APIRouter()


def get_service(request: Request) -> GuardrailService:
    return request.app.state.service


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/v1/detect", response_model=DetectResponse, tags=["detection"])
def detect(body: DetectRequest, service: GuardrailService = Depends(get_service)) -> DetectResponse:
    """API 1 — 'Tell me what PII is in this prompt.' Never modifies the prompt."""
    detections = service.detect(body.prompt)
    entities = [
        DetectedEntity(type=d.entity_type, confidence=d.confidence, start=d.start, end=d.end)
        for d in detections
    ]
    logger.info(
        "detect",
        extra=safe_extra(
            event="detect",
            detection_count=len(entities),
            entity_types=sorted({e.type for e in entities}),
        ),
    )
    return DetectResponse(detections=entities, detection_count=len(entities))


@router.post("/v1/redact", response_model=RedactResponse, tags=["redaction"])
def redact_endpoint(
    body: RedactRequest, service: GuardrailService = Depends(get_service)
) -> RedactResponse:
    """API 2 — 'Given this prompt and these options, protect the PII.'

    Fails closed: if detection is unavailable, the request is blocked (no content
    returned) rather than returning the unprotected prompt.
    """
    opts = body.options
    options = RedactionOptions(
        entities=frozenset(opts.entities) if opts and opts.entities is not None else None,
        strategy_per_type=dict(opts.strategy_per_type) if opts else {},
        default_strategy=opts.default_strategy if opts else "redact",
        mask_keep_last=opts.mask_keep_last if opts else 4,
        mask_char=opts.mask_char if opts else "*",
    )
    result, detections = service.redact(body.prompt, options)
    actions = [ActionSummary(type=a.entity_type, action=a.action, count=a.count) for a in result.actions]
    logger.info(
        "redact",
        extra=safe_extra(
            event="redact",
            detection_count=len(detections),
            action_counts=sum(a.count for a in actions),
            outcome="transformed" if actions else "allowed",
        ),
    )
    return RedactResponse(
        redacted_prompt=result.text,
        actions=actions,
        detection_count=len(detections),
    )


def register_exception_handlers(app) -> None:
    from ..core.errors import GuardrailError

    @app.exception_handler(GuardrailError)
    async def _guardrail_error_handler(request: Request, exc: GuardrailError):  # noqa: ANN001
        # Redaction fails closed: block (no content) instead of leaking an unprotected prompt.
        status = exc.http_status
        code = exc.code
        if isinstance(exc, DetectionUnavailableError) and request.url.path.endswith("/redact"):
            status = 422
            code = "blocked"
        logger.warning(
            "request_failed",
            extra=safe_extra(event="error", error_kind=code, status_code=status),
        )
        return JSONResponse(status_code=status, content={"code": code, "message": exc.message})
