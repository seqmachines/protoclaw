import pytest
from pydantic import BaseModel

from protocrawl.llm import gemini


class _FlexiblePayload(BaseModel):
    items: list[dict]


def test_sanitize_json_schema_removes_additional_properties():
    schema = {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": True,
                },
            }
        },
        "additionalProperties": False,
    }

    cleaned = gemini._sanitize_json_schema(schema)

    assert "additionalProperties" not in cleaned
    assert "additionalProperties" not in cleaned["properties"]["items"]["items"]


@pytest.mark.asyncio
async def test_extract_structured_falls_back_when_schema_mode_fails(
    monkeypatch: pytest.MonkeyPatch,
):
    class DummyTypes:
        class GenerateContentConfig:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

    class DummyModels:
        async def generate_content(self, **kwargs):
            raise RuntimeError("additionalProperties is not supported in the Gemini API.")

    class DummyAio:
        models = DummyModels()

    class DummyClient:
        aio = DummyAio()

    async def fake_generate(prompt: str, *, system: str | None = None, max_tokens: int = 8192) -> str:
        return '{"items":[{"a":"b"}]}'

    monkeypatch.setattr(gemini, "get_client", lambda: DummyClient())
    monkeypatch.setattr(gemini, "_load_genai", lambda: (object(), DummyTypes))
    monkeypatch.setattr(gemini, "generate", fake_generate)

    result = await gemini.extract_structured("prompt", _FlexiblePayload)

    assert result.items == [{"a": "b"}]
