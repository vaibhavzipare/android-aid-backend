from __future__ import annotations

import json
import logging

from groq import Groq
from pydantic import ValidationError

from app.schemas import AnalyzeErrorResponse, ErrorContext

logger = logging.getLogger("android_aid_backend")


class GroqLLMService:
    """Groq-powered Android error analysis service."""

    def __init__(self, api_key: str, model: str):
        self.client = Groq(api_key=api_key)
        self.model = model

    def analyze(
        self,
        error_text: str,
        context: ErrorContext | None,
    ) -> AnalyzeErrorResponse:
        prompt = self._build_prompt(error_text, context)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are Android Aid, an expert Android Studio "
                        "debugging assistant. Analyze Android errors and "
                        "return ONLY valid JSON matching the requested schema."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content

        if not content:
            raise ValueError("Groq returned an empty response.")

        try:
            data = json.loads(content)
            return AnalyzeErrorResponse.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.exception("Invalid JSON/schema returned by Groq.")
            raise ValueError(
                "Groq returned an invalid analysis response."
            ) from exc

    def _build_prompt(
        self,
        error_text: str,
        context: ErrorContext | None,
    ) -> str:
        context_text = (
            context.model_dump_json()
            if context is not None
            else "No project context provided."
        )

        return f"""
Analyze this Android Studio error.

ERROR:
{error_text}

PROJECT CONTEXT:
{context_text}

Return JSON with exactly this structure:

{{
  "error_type": "short error category",
  "explanation": "clear explanation of what caused the error",
  "fixes": [
    {{
      "title": "fix title",
      "steps": [
        "step 1",
        "step 2",
        "step 3"
      ],
      "code_patches": [
        {{
          "file": "path/to/file",
          "code": "replacement or example code"
        }}
      ],
      "commands": [
        "command 1"
      ]
    }}
  ]
}}

Rules:
- Give practical Android Studio fixes.
- Give 1-3 fixes.
- Keep steps clear and beginner-friendly.
- Only provide code patches when useful.
- Only provide commands when useful.
- Do not use Markdown.
- Return valid JSON only.
""".strip()