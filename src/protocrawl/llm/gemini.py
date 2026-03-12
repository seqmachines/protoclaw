"""Gemini API client with typed structured-output helpers."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from protocrawl.config import settings


def _load_genai():
    from google import genai
    from google.genai import types

    return genai, types


def get_client():
    """Create a Gemini API client.

    If `PROTOCRAWL_GEMINI_API_KEY` is unset, the SDK can still fall back
    to `GOOGLE_API_KEY` from the environment.
    """
    genai, _ = _load_genai()
    if settings.gemini_api_key:
        return genai.Client(api_key=settings.gemini_api_key)
    return genai.Client()


def _sanitize_json_schema(value: Any) -> Any:
    """Remove schema features that Gemini rejects in structured output mode."""
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            if key == "additionalProperties":
                continue
            cleaned[key] = _sanitize_json_schema(item)
        return cleaned
    if isinstance(value, list):
        return [_sanitize_json_schema(item) for item in value]
    return value


async def generate(
    prompt: str,
    *,
    system: str | None = None,
    max_tokens: int = 8192,
) -> str:
    """Generate free-form text from Gemini."""
    client = get_client()
    _, types = _load_genai()
    config = types.GenerateContentConfig(
        system_instruction=system,
        max_output_tokens=max_tokens,
        temperature=0,
    )
    response = await client.aio.models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
        config=config,
    )
    return response.text or ""


async def extract_structured(
    prompt: str,
    response_model: type[BaseModel],
    *,
    system: str | None = None,
    max_tokens: int = 8192,
) -> BaseModel:
    """Generate JSON matching a Pydantic response model."""
    client = get_client()
    _, types = _load_genai()
    schema = _sanitize_json_schema(response_model.model_json_schema())
    config = types.GenerateContentConfig(
        system_instruction=system,
        response_mime_type="application/json",
        response_json_schema=schema,
        max_output_tokens=max_tokens,
        temperature=0,
    )
    try:
        response = await client.aio.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=config,
        )

        parsed = getattr(response, "parsed", None)
        if parsed is not None:
            if isinstance(parsed, response_model):
                return parsed
            return response_model.model_validate(parsed)

        return response_model.model_validate_json(response.text or "{}")
    except Exception as exc:
        # Fall back to prompt-only JSON generation if schema-based output is rejected.
        schema_json = json.dumps(schema, indent=2)
        json_instruction = (
            "Respond ONLY with valid JSON matching this schema:\n"
            f"```json\n{schema_json}\n```\n"
            "No markdown, no explanation, just the JSON object."
        )
        full_system = json_instruction if system is None else f"{system}\n\n{json_instruction}"
        raw = await generate(prompt, system=full_system, max_tokens=max_tokens)
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines)

        try:
            return response_model.model_validate_json(cleaned)
        except Exception:
            raise exc
