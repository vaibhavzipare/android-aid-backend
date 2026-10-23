"""Pydantic v2 request/response models for the Android Aid API."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class ErrorContext(BaseModel):
    """Optional project context supplied alongside the raw error text."""

    agp_version: str | None = Field(default=None, description="Android Gradle Plugin version")
    gradle_version: str | None = Field(default=None, description="Gradle wrapper version")
    jdk_version: str | None = Field(default=None, description="JDK version in use")
    kotlin_version: str | None = Field(default=None, description="Kotlin plugin version")
    compose_version: str | None = Field(default=None, description="Jetpack Compose compiler/BOM version")
    other: str | None = Field(default=None, description="Any other free-form project context")


class AnalyzeErrorRequest(BaseModel):
    """Incoming payload for POST /analyze-error."""

    error_text: str = Field(min_length=1, description="Raw error/log text from Android Studio")
    context: ErrorContext | None = Field(default=None)

    @field_validator("error_text")
    @classmethod
    def error_text_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("error_text must not be blank")
        return value


class CodePatch(BaseModel):
    """A suggested code change, optionally scoped to a specific file."""

    file: str | None = Field(default=None, description="File the patch applies to, if known")
    code: str = Field(description="The suggested code snippet or patch content")


class Fix(BaseModel):
    """A single actionable fix suggestion."""

    title: str
    steps: list[str] = Field(default_factory=list)
    code_patches: list[CodePatch] = Field(default_factory=list)
    commands: list[str] = Field(default_factory=list)


class AnalyzeErrorResponse(BaseModel):
    """Structured fix plan returned by POST /analyze-error."""

    error_type: str
    explanation: str
    fixes: list[Fix]


class HealthResponse(BaseModel):
    """Response body for GET /health."""

    status: str
    version: str
    app: str


class ErrorDetail(BaseModel):
    """Standard error envelope for 4xx/5xx responses."""

    detail: str
