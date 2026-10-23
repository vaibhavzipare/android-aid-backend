"""FastAPI application entrypoint for Android Aid backend."""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from app.config import Settings, get_settings
from app.groq_llm_service import GroqLLMService
from app.mock_llm_service import LLMService, MockLLMService
from app.schemas import AnalyzeErrorRequest, AnalyzeErrorResponse, HealthResponse

logger = logging.getLogger("android_aid_backend")
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Android Aid Backend",
    description="Backend API that analyzes Android Studio errors and returns structured fix plans.",
    version="0.1.0",
)

_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_llm_service(settings: Annotated[Settings, Depends(get_settings)]) -> LLMService:
    """Dependency provider for the error-analysis service.

    Returns a real Groq-backed service when GROQ_API_KEY is configured;
    otherwise falls back to the rule-based mock.
    """
    if settings.groq_api_key:
        return GroqLLMService(api_key=settings.groq_api_key, model=settings.groq_model)
    return MockLLMService()


@app.get("/health", response_model=HealthResponse)
def health(settings: Annotated[Settings, Depends(get_settings)]) -> HealthResponse:
    return HealthResponse(status="ok", version=settings.app_version, app=settings.app_name)


@app.post("/analyze-error", response_model=AnalyzeErrorResponse)
def analyze_error(
    request: AnalyzeErrorRequest,
    llm_service: Annotated[LLMService, Depends(get_llm_service)],
) -> AnalyzeErrorResponse:
    try:
        return llm_service.analyze(request.error_text, request.context)
    except ValidationError as exc:
        logger.warning("Validation error while analyzing error text: %s", exc)
        raise HTTPException(status_code=400, detail="Invalid request payload.") from exc
    except Exception as exc:  # noqa: BLE001 - convert any unexpected failure to a 500
        logger.exception("Unexpected failure during error analysis")
        raise HTTPException(status_code=500, detail="Internal error while analyzing error text.") from exc
