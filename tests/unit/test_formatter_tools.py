"""Tests for formatter tools."""

import json

from protocrawl.agents.formatter.tools import (
    format_protocol,
    generate_json,
    generate_summary,
    render_read_diagram,
)
from protocrawl.models import (
    AssayFamily,
    BarcodeSpec,
    MoleculeType,
    Protocol,
    ReadGeometry,
    ReadSegment,
    ReadType,
    SegmentRole,
)


def _sample_protocol() -> Protocol:
    return Protocol(
        slug="10x-chromium-3prime-v3",
        name="10x Chromium 3' v3",
        version="v3",
        assay_family=AssayFamily.SCRNA_SEQ,
        molecule_type=MoleculeType.RNA,
        description="Droplet-based single-cell RNA-seq.",
        vendor="10x Genomics",
        platform="Illumina",
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
                ),
                ReadSegment(
                    role=SegmentRole.UMI,
                    read_number=1,
                    start_pos=16,
                    length=12,
                ),
                ReadSegment(
                    role=SegmentRole.CDNA,
                    read_number=2,
                    start_pos=0,
                    length=91,
                ),
                ReadSegment(
                    role=SegmentRole.SAMPLE_INDEX,
                    read_number=3,
                    start_pos=0,
                    length=8,
                ),
            ],
        ),
        barcodes=[
            BarcodeSpec(
                role=SegmentRole.CELL_BARCODE,
                length=16,
                addition_method="ligation",
            ),
            BarcodeSpec(role=SegmentRole.UMI, length=12),
        ],
        caveats=["Requires Illumina sequencer"],
        confidence_score=0.92,
    )


class TestRenderReadDiagram:
    def test_contains_read_labels(self):
        diagram = render_read_diagram(_sample_protocol())
        assert "Read 1" in diagram
        assert "Read 2" in diagram
        assert "Index 1" in diagram

    def test_contains_segment_info(self):
        diagram = render_read_diagram(_sample_protocol())
        assert "16bp" in diagram
        assert "12bp" in diagram
        assert "91bp" in diagram

    def test_contains_protocol_name(self):
        diagram = render_read_diagram(_sample_protocol())
        assert "10x Chromium 3' v3" in diagram


class TestGenerateSummary:
    def test_contains_protocol_name(self):
        summary = generate_summary(_sample_protocol())
        assert "10x Chromium 3' v3" in summary

    def test_contains_assay_family(self):
        summary = generate_summary(_sample_protocol())
        assert "scRNA-seq" in summary

    def test_contains_vendor(self):
        summary = generate_summary(_sample_protocol())
        assert "10x Genomics" in summary

    def test_contains_caveats(self):
        summary = generate_summary(_sample_protocol())
        assert "Illumina sequencer" in summary

    def test_contains_barcode_info(self):
        summary = generate_summary(_sample_protocol())
        assert "16bp" in summary


class TestGenerateJson:
    def test_valid_json(self):
        output = generate_json(_sample_protocol())
        data = json.loads(output)
        assert data["slug"] == "10x-chromium-3prime-v3"
        assert data["assay_family"] == "scRNA-seq"

    def test_roundtrip(self):
        output = generate_json(_sample_protocol())
        data = json.loads(output)
        restored = Protocol.model_validate(data)
        assert restored.slug == "10x-chromium-3prime-v3"


class TestFormatProtocol:
    def test_returns_all_fields(self):
        result = format_protocol(_sample_protocol())
        assert result.slug == "10x-chromium-3prime-v3"
        assert len(result.read_diagram) > 0
        assert len(result.summary) > 0
        assert len(result.json_output) > 0
