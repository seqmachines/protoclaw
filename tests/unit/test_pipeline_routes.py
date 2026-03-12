from fastapi import FastAPI
from fastapi.testclient import TestClient

from protocrawl.api.routes import pipeline


def test_pipeline_draft_route(monkeypatch):
    app = FastAPI()
    app.include_router(pipeline.router, prefix="/pipeline")

    async def fake_build_protocol_draft(*, source_ref=None, source_text=None, toolkit=None):
        return {
            "source_document": {"url": source_ref or "inline://text"},
            "protocol": {"name": "Chromium GEM-X"},
            "seqspec": {"assay_id": "chromium-gem-x"},
        }

    monkeypatch.setattr(pipeline, "build_protocol_draft", fake_build_protocol_draft)

    client = TestClient(app)
    response = client.post("/pipeline/draft", json={"source_text": "protocol text"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["protocol"]["name"] == "Chromium GEM-X"
    assert payload["source_document"]["url"] == "inline://text"
