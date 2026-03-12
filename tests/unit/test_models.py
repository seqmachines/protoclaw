import uuid

import pytest
from pydantic import ValidationError

from protocrawl.models import (
    Adapter,
    AssayFamily,
    BarcodeSpec,
    Citation,
    ConfidenceLevel,
    FailureMode,
    MoleculeType,
    Protocol,
    QCExpectation,
    ReadGeometry,
    ReadSegment,
    ReadType,
    ReviewRequest,
    ReviewStatus,
    SegmentRole,
    SourceDocument,
)


def _minimal_protocol(**overrides) -> Protocol:
    defaults = dict(
        slug="10x-chromium-3prime-v3",
        name="10x Chromium 3' v3",
        version="v3",
        assay_family=AssayFamily.SCRNA_SEQ,
        molecule_type=MoleculeType.RNA,
        description="Single-cell RNA-seq using 10x Chromium 3' v3 chemistry.",
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
            ],
        ),
        confidence_score=0.9,
    )
    defaults.update(overrides)
    return Protocol(**defaults)


class TestProtocolModel:
    def test_create_minimal(self):
        p = _minimal_protocol()
        assert p.slug == "10x-chromium-3prime-v3"
        assert p.assay_family == AssayFamily.SCRNA_SEQ
        assert isinstance(p.id, uuid.UUID)

    def test_confidence_level_high(self):
        p = _minimal_protocol(confidence_score=0.9)
        assert p.confidence_level == ConfidenceLevel.HIGH

    def test_confidence_level_medium(self):
        p = _minimal_protocol(confidence_score=0.7)
        assert p.confidence_level == ConfidenceLevel.MEDIUM

    def test_confidence_level_low(self):
        p = _minimal_protocol(confidence_score=0.4)
        assert p.confidence_level == ConfidenceLevel.LOW

    def test_confidence_score_bounds(self):
        with pytest.raises(ValidationError):
            _minimal_protocol(confidence_score=1.5)
        with pytest.raises(ValidationError):
            _minimal_protocol(confidence_score=-0.1)

    def test_serialization_roundtrip(self):
        p = _minimal_protocol(
            adapters=[
                Adapter(name="P5", sequence="AATGATACGGCGACCACCGA", position="5prime")
            ],
            barcodes=[BarcodeSpec(role=SegmentRole.CELL_BARCODE, length=16)],
            citations=[Citation(title="Zheng et al. 2017", doi="10.1038/ncomms14049")],
            qc_expectations=[
                QCExpectation(
                    metric="genes_per_cell",
                    typical_range_low=500,
                    typical_range_high=5000,
                )
            ],
            failure_modes=[
                FailureMode(
                    description="Low cell recovery",
                    symptom="<500 cells",
                    likely_cause="Clogged chip",
                )
            ],
        )
        data = p.model_dump(mode="json")
        p2 = Protocol.model_validate(data)
        assert p2.slug == p.slug
        assert len(p2.adapters) == 1
        assert len(p2.citations) == 1
        assert p2.adapters[0].sequence == "AATGATACGGCGACCACCGA"

    def test_default_review_status(self):
        p = _minimal_protocol()
        assert p.review_status == ReviewStatus.PENDING

    def test_default_schema_version(self):
        p = _minimal_protocol()
        assert p.schema_version == "1.0.0"


class TestReadGeometry:
    def test_empty_segments(self):
        rg = ReadGeometry(read_type=ReadType.SINGLE_END)
        assert rg.segments == []

    def test_segments_with_variable_length(self):
        seg = ReadSegment(
            role=SegmentRole.CDNA, read_number=2, start_pos=0, length=None
        )
        assert seg.length is None


class TestEnums:
    def test_assay_family_values(self):
        assert AssayFamily.SCRNA_SEQ == "scRNA-seq"
        assert AssayFamily.CITE_SEQ == "CITE-seq"

    def test_segment_role_values(self):
        assert SegmentRole.CELL_BARCODE == "cell_barcode"
        assert SegmentRole.UMI == "umi"


class TestSourceDocument:
    def test_create(self):
        s = SourceDocument(
            url="https://arxiv.org/abs/1234.5678", source_type="preprint"
        )
        assert s.url == "https://arxiv.org/abs/1234.5678"
        assert s.raw_text is None
        assert isinstance(s.id, uuid.UUID)


class TestReviewRequest:
    def test_create(self):
        protocol_id = uuid.uuid4()
        r = ReviewRequest(protocol_id=protocol_id, confidence_score=0.65)
        assert r.status == ReviewStatus.PENDING
        assert r.confidence_score == 0.65
