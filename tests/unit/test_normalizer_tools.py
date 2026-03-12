"""Tests for normalizer tools."""

from protocrawl.agents.normalizer.tools import (
    _slugify,
    compute_confidence,
    normalize_to_schema,
)
from protocrawl.models.enums import AssayFamily, MoleculeType


class TestSlugify:
    def test_basic(self):
        assert _slugify("Drop-seq") == "drop-seq"

    def test_with_version(self):
        assert _slugify("10x Chromium 3' v3", "v3") == "10x-chromium-3-v3-v3"

    def test_special_chars(self):
        assert _slugify("SMART-seq2", "v2") == "smart-seq2-v2"


class TestComputeConfidence:
    def test_full_extraction_high_confidence(self):
        result = compute_confidence(
            metadata={
                "name": "Test Protocol",
                "assay_family": "scRNA-seq",
                "molecule_type": "RNA",
                "description": "A test protocol.",
            },
            read_structure={
                "read_type": "paired-end",
                "read1_length": 28,
                "read2_length": 91,
                "segments": [
                    {
                        "role": "cell_barcode",
                        "read_number": 1,
                        "start_pos": 0,
                        "length": 16,
                    },
                    {
                        "role": "umi",
                        "read_number": 1,
                        "start_pos": 16,
                        "length": 12,
                    },
                ],
            },
            barcodes=[
                {"role": "cell_barcode", "length": 16},
                {"role": "umi", "length": 12},
            ],
            citations=[
                {"doi": "10.1234/test", "title": "Test paper"},
            ],
            protocol_details={
                "protocol_steps": ["Step 1", "Step 2"],
                "qc_metrics": [{"metric": "genes_per_cell", "typical_range_low": 500}],
            },
        )
        assert result["score"] >= 0.85
        assert result["level"] == "high"

    def test_minimal_extraction_low_confidence(self):
        result = compute_confidence(
            metadata={"name": "Unknown"},
        )
        assert result["score"] < 0.60
        assert result["level"] == "low"
        assert len(result["issues"]) > 0

    def test_no_metadata_very_low(self):
        result = compute_confidence()
        assert result["score"] < 0.30
        assert "No metadata extracted" in result["issues"]

    def test_segment_length_mismatch_flagged(self):
        result = compute_confidence(
            metadata={
                "name": "Test",
                "assay_family": "scRNA-seq",
                "description": "Test",
            },
            read_structure={
                "read_type": "paired-end",
                "read1_length": 28,
                "segments": [
                    {
                        "role": "cell_barcode",
                        "read_number": 1,
                        "start_pos": 0,
                        "length": 20,
                    },
                    {
                        "role": "umi",
                        "read_number": 1,
                        "start_pos": 20,
                        "length": 15,
                    },
                ],
            },
        )
        assert any("segments total 35bp" in i for i in result["issues"])

    def test_assay_molecule_mismatch_flagged(self):
        result = compute_confidence(
            metadata={
                "name": "Test",
                "assay_family": "scRNA-seq",
                "molecule_type": "chromatin",
                "description": "Test",
            },
            read_structure={
                "read_type": "paired-end",
                "segments": [
                    {
                        "role": "cdna",
                        "read_number": 1,
                        "start_pos": 0,
                        "length": 50,
                    }
                ],
            },
        )
        assert any("typically uses" in i for i in result["issues"])


class TestNormalizeToSchema:
    def test_full_normalization(self):
        protocol = normalize_to_schema(
            metadata={
                "name": "Test Protocol",
                "version": "v2",
                "assay_family": "scRNA-seq",
                "molecule_type": "RNA",
                "description": "A test protocol for unit testing.",
                "vendor": "TestCo",
                "platform": "Illumina",
            },
            read_structure={
                "read_type": "paired-end",
                "read1_length": 28,
                "read2_length": 91,
                "segments": [
                    {
                        "role": "cell_barcode",
                        "read_number": 1,
                        "start_pos": 0,
                        "length": 16,
                    },
                    {
                        "role": "umi",
                        "read_number": 1,
                        "start_pos": 16,
                        "length": 12,
                    },
                    {
                        "role": "cdna",
                        "read_number": 2,
                        "start_pos": 0,
                        "length": 91,
                    },
                ],
            },
            barcodes=[
                {"role": "cell_barcode", "length": 16, "addition_method": "ligation"},
                {"role": "umi", "length": 12},
            ],
            adapters=[
                {
                    "name": "TruSeq Read 1",
                    "sequence": "CTACACGACGCTCTTCCGATCT",
                    "position": "5prime",
                }
            ],
            citations=[{"doi": "10.1234/test", "title": "Test paper", "year": 2020}],
            protocol_details={
                "protocol_steps": ["Step 1", "Step 2"],
                "qc_metrics": [
                    {
                        "metric": "genes_per_cell",
                        "typical_range_low": 500,
                        "typical_range_high": 5000,
                    }
                ],
                "failure_modes": [
                    {
                        "description": "Low recovery",
                        "symptom": "Few cells",
                        "likely_cause": "Bad loading",
                    }
                ],
                "caveats": ["Test caveat"],
            },
            source_urls=["https://example.com/protocol"],
        )

        assert protocol.name == "Test Protocol"
        assert protocol.slug == "test-protocol-v2"
        assert protocol.assay_family == AssayFamily.SCRNA_SEQ
        assert protocol.molecule_type == MoleculeType.RNA
        assert protocol.vendor == "TestCo"
        assert len(protocol.read_geometry.segments) == 3
        assert len(protocol.barcodes) == 2
        assert len(protocol.adapters) == 1
        assert len(protocol.citations) == 1
        assert len(protocol.qc_expectations) == 1
        assert len(protocol.failure_modes) == 1
        assert len(protocol.caveats) == 1
        assert protocol.confidence_score > 0
        assert protocol.source_urls == ["https://example.com/protocol"]

    def test_minimal_normalization(self):
        protocol = normalize_to_schema(
            metadata={
                "name": "Bare Protocol",
                "assay_family": "other",
                "molecule_type": "RNA",
                "description": "Minimal.",
            },
        )
        assert protocol.name == "Bare Protocol"
        assert protocol.slug == "bare-protocol"
        assert protocol.version == "v1"
        assert protocol.confidence_score < 0.60

    def test_empty_normalization(self):
        protocol = normalize_to_schema()
        assert protocol.name == "Unknown Protocol"
        assert protocol.confidence_score < 0.30
