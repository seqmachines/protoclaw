import json

from protocrawl.agents.formatter.tools import generate_seqspec_json, generate_seqspec_yaml
from protocrawl.agents.normalizer.tools import seqspec_to_protocol
from protocrawl.models import SeqSpec, SeqSpecRead, SeqSpecRegion
from protocrawl.models.enums import SegmentRole


def _sample_seqspec() -> SeqSpec:
    return SeqSpec(
        assay_id="10x-gemx-3prime-v4-csp",
        name="Chromium GEM-X Single Cell 3' v4 Cell Surface Protein",
        description="Seqspec extraction for a 10x GEM-X assay.",
        modalities=["rna", "protein"],
        library_spec=[
            SeqSpecRegion(
                region_id="R1_PRIMER",
                region_type="primer",
                sequence_type="fixed",
                sequence="CTACACGACGCTCTTCCGATCT",
                regions=[
                    SeqSpecRegion(
                        region_id="CELLBC",
                        region_type="barcode",
                        sequence_type="onlist",
                        min_len=16,
                        max_len=16,
                    ),
                    SeqSpecRegion(
                        region_id="UMI",
                        region_type="umi",
                        sequence_type="random",
                        min_len=12,
                        max_len=12,
                        regions=[
                            SeqSpecRegion(
                                region_id="CDNA",
                                region_type="cdna",
                                sequence_type="random",
                                min_len=90,
                                max_len=90,
                            )
                        ],
                    ),
                ],
            )
        ],
        sequence_spec=[
            SeqSpecRead(read_id="R1", primer_id="R1_PRIMER", min_len=28, max_len=28),
            SeqSpecRead(read_id="R2", primer_id="UMI", min_len=90, max_len=90),
        ],
        source_urls=["https://example.com/protocol.pdf"],
    )


def test_seqspec_to_protocol_builds_read_geometry():
    protocol = seqspec_to_protocol(_sample_seqspec())

    assert protocol.slug == "10x-gemx-3prime-v4-csp"
    assert protocol.read_geometry.read1_length == 28
    assert protocol.read_geometry.read2_length == 90
    assert any(seg.role == SegmentRole.CELL_BARCODE for seg in protocol.read_geometry.segments)
    assert any(seg.role == SegmentRole.UMI for seg in protocol.read_geometry.segments)


def test_generate_seqspec_json_roundtrip():
    output = generate_seqspec_json(_sample_seqspec())
    data = json.loads(output)

    assert data["assay_id"] == "10x-gemx-3prime-v4-csp"
    assert data["sequence_spec"][0]["primer_id"] == "R1_PRIMER"


def test_generate_seqspec_yaml_contains_top_level_fields():
    output = generate_seqspec_yaml(_sample_seqspec())

    assert "assay_id: 10x-gemx-3prime-v4-csp" in output
    assert "library_spec:" in output
    assert "sequence_spec:" in output
