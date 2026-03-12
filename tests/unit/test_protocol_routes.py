from fastapi import FastAPI
from fastapi.testclient import TestClient
from types import SimpleNamespace

from protocrawl.api.dependencies import get_db
from protocrawl.api.routes import protocols
from protocrawl.models import (
    AssayFamily,
    FieldEvidence,
    MoleculeType,
    Protocol,
    ProtocolTimelineStep,
    ReadGeometry,
    ReadSegment,
    ReadType,
    ReviewStatus,
    SegmentRole,
)


def _protocol() -> Protocol:
    return Protocol(
        slug="demo-protocol",
        name="Demo Protocol",
        version="v1",
        chemistry_version="v1.1",
        assay_family=AssayFamily.SCRNA_SEQ,
        molecule_type=MoleculeType.RNA,
        description="Demo explorer payload.",
        vendor="Demo Vendor",
        platform="Illumina",
        compatible_instruments=["Illumina NextSeq"],
        read_geometry=ReadGeometry(
            read_type=ReadType.PAIRED_END,
            read1_length=28,
            read2_length=91,
            index1_length=8,
            segments=[
                ReadSegment(
                    role=SegmentRole.CELL_BARCODE,
                    read_number=1,
                    start_pos=0,
                    length=16,
                    description="Cell barcode",
                ),
                ReadSegment(
                    role=SegmentRole.UMI,
                    read_number=1,
                    start_pos=16,
                    length=12,
                    description="UMI",
                ),
                ReadSegment(
                    role=SegmentRole.CDNA,
                    read_number=2,
                    start_pos=0,
                    length=91,
                    description="Insert",
                ),
            ],
        ),
        protocol_steps=["Step A", "Step B"],
        protocol_timeline=[
            ProtocolTimelineStep(
                step_id="step-a",
                title="Step A",
                introduced_segment_ids=["read-seg-1"],
            )
        ],
        field_evidence=[
            FieldEvidence(
                field_path="name",
                label="Assay name",
                value="Demo Protocol",
                extraction_mode="extracted",
                confidence_score=0.96,
                review_status=ReviewStatus.APPROVED,
            )
        ],
        parser_config={"schema": "Protocol"},
        source_urls=["https://example.com/protocol"],
        confidence_score=0.91,
    )


async def _fake_get_db():
    yield None


def test_protocol_explorer_route(monkeypatch):
    app = FastAPI()
    app.include_router(protocols.router, prefix="/protocols")
    app.dependency_overrides[get_db] = _fake_get_db

    async def fake_get_protocol_by_slug(db, slug: str):
        assert slug == "demo-protocol"
        return SimpleNamespace(id="protocol-row")

    monkeypatch.setattr(protocols.repo, "get_protocol_by_slug", fake_get_protocol_by_slug)
    monkeypatch.setattr(protocols, "row_to_protocol", lambda row: _protocol())

    client = TestClient(app)
    response = client.get("/protocols/demo-protocol/explorer")

    assert response.status_code == 200
    payload = response.json()
    assert payload["header"]["assay_name"] == "Demo Protocol"
    assert payload["recipe"]["read1_length"] == 28
    assert payload["timeline"][0]["step_id"] == "step-a"
    assert payload["blueprint_segments"][0]["segment_id"] == "read-seg-1"


def test_protocol_export_routes(monkeypatch):
    app = FastAPI()
    app.include_router(protocols.router, prefix="/protocols")
    app.dependency_overrides[get_db] = _fake_get_db

    async def fake_get_protocol_by_slug(db, slug: str):
        assert slug == "demo-protocol"
        return SimpleNamespace(id="protocol-row")

    async def fake_get_protocol_seqspec(db, protocol_id):
        return None

    monkeypatch.setattr(protocols.repo, "get_protocol_by_slug", fake_get_protocol_by_slug)
    monkeypatch.setattr(protocols.repo, "get_protocol_seqspec", fake_get_protocol_seqspec)
    monkeypatch.setattr(protocols, "row_to_protocol", lambda row: _protocol())

    client = TestClient(app)

    parser_response = client.get("/protocols/demo-protocol/exports/parser-config")
    assert parser_response.status_code == 200
    assert parser_response.json()["schema"] == "Protocol"

    tsv_response = client.get("/protocols/demo-protocol/exports/tsv")
    assert tsv_response.status_code == 200
    assert "field\tvalue" in tsv_response.text
    assert "read_structure\tR1[Cell barcode:16, UMI:12] | R2[Insert:91]" in tsv_response.text

    seqspec_response = client.get("/protocols/demo-protocol/seqspec?format=json")
    assert seqspec_response.status_code == 200
    assert seqspec_response.json()["name"] == "Demo Protocol"
