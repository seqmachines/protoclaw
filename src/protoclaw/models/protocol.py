from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from protoclaw.models.enums import (
    AssayFamily,
    ConfidenceLevel,
    MoleculeType,
    ReadType,
    ReviewStatus,
    SegmentRole,
)


class ReadSegment(BaseModel):
    """A contiguous region within a sequencing read."""

    role: SegmentRole
    read_number: int  # 1=Read1, 2=Read2, 3=Index1, 4=Index2
    start_pos: int  # 0-based position within the read
    length: int | None = None  # None = variable length
    sequence: str | None = None  # Fixed sequence if known (e.g., linker)
    description: str | None = None


class ReadGeometry(BaseModel):
    """Complete read layout for a protocol."""

    read_type: ReadType
    read1_length: int | None = None
    read2_length: int | None = None
    index1_length: int | None = None
    index2_length: int | None = None
    segments: list[ReadSegment] = []


class Adapter(BaseModel):
    name: str  # e.g., "Illumina P5", "TruSeq Read 1"
    sequence: str
    position: str  # "5prime" | "3prime" | "internal"


class BarcodeSpec(BaseModel):
    """Barcode/UMI specification."""

    role: SegmentRole  # cell_barcode, umi, sample_index, feature_barcode
    length: int
    whitelist_source: str | None = None  # URL or filename of barcode whitelist
    addition_method: str | None = None  # "ligation", "PCR", "template_switch", etc.


class ReagentKit(BaseModel):
    name: str
    vendor: str
    catalog_number: str | None = None
    version: str | None = None


class Citation(BaseModel):
    doi: str | None = None
    pmid: str | None = None
    arxiv_id: str | None = None
    title: str
    authors: list[str] = []
    year: int | None = None
    url: str | None = None


class LibraryRegion(BaseModel):
    """A single region in the final library structure visualization."""

    type: str  # p5, p7, s5, s7, cbc, umi, me, cdna, index, tso, linker, etc.
    top: str  # Top strand sequence text (5'->3')
    bottom: str  # Bottom strand complement text (3'->5')
    label: str | None = None  # Annotation label displayed below


class QCExpectation(BaseModel):
    metric: str  # e.g., "reads_per_cell", "genes_per_cell"
    typical_range_low: float | None = None
    typical_range_high: float | None = None
    notes: str | None = None


class FailureMode(BaseModel):
    description: str
    symptom: str
    likely_cause: str
    mitigation: str | None = None


class FieldEvidence(BaseModel):
    """Traceable provenance for a protocol field or segment."""

    field_path: str
    label: str
    value: str | None = None
    segment_id: str | None = None
    source_url: str | None = None
    excerpt: str | None = None
    page_reference: str | None = None
    extraction_mode: str = "extracted"  # extracted | inferred
    confidence_score: float | None = Field(default=None, ge=0.0, le=1.0)
    review_status: ReviewStatus | None = None
    parser_stage: str | None = None
    parser_source: str | None = None
    notes: str | None = None


class ProtocolTimelineStep(BaseModel):
    """A user-facing step in library generation."""

    step_id: str
    title: str
    summary: str | None = None
    introduced_segment_ids: list[str] = []
    modified_segment_ids: list[str] = []
    highlighted_field_paths: list[str] = []


class ExplorerSegmentReadMapping(BaseModel):
    read_key: str
    label: str
    start_cycle: int
    end_cycle: int


class ExplorerSegment(BaseModel):
    segment_id: str
    label: str
    kind: str
    role: SegmentRole | None = None
    sequence: str | None = None
    length: int | None = None
    description: str | None = None
    introduced_by_step_id: str | None = None
    modified_by_step_ids: list[str] = []
    preprocessing_group: str | None = None
    read_mappings: list[ExplorerSegmentReadMapping] = []


class ExplorerReadTrace(BaseModel):
    read_key: str
    label: str
    length: int | None = None
    segments: list[str] = []


class ExplorerPreprocessingGroup(BaseModel):
    group_id: str
    label: str
    description: str | None = None
    segment_ids: list[str] = []


class ProtocolExplorerHeader(BaseModel):
    assay_name: str
    chemistry_version: str | None = None
    assay_family: AssayFamily
    vendor: str | None = None
    compatible_instruments: list[str] = []
    confidence_score: float
    review_status: ReviewStatus
    source_links: list[str] = []
    last_updated: datetime | None = None
    revision: str | None = None


class SequencingRecipe(BaseModel):
    read1_length: int | None = None
    read2_length: int | None = None
    index1_length: int | None = None
    index2_length: int | None = None
    custom_primer_required: bool | None = None
    supported_instruments: list[str] = []
    orientation_notes: str | None = None
    read_structure_string: str | None = None


class ExportArtifact(BaseModel):
    export_id: str
    label: str
    format: str
    href: str | None = None
    copy_text: str | None = None


class ProtocolExplorer(BaseModel):
    header: ProtocolExplorerHeader
    blueprint_segments: list[ExplorerSegment] = []
    sequencer_reads: list[ExplorerReadTrace] = []
    preprocessing_groups: list[ExplorerPreprocessingGroup] = []
    timeline: list[ProtocolTimelineStep] = []
    recipe: SequencingRecipe
    evidence: list[FieldEvidence] = []
    exports: list[ExportArtifact] = []
    citations: list[Citation] = []
    description: str | None = None
    extraction_notes: str | None = None


def _confidence_level(score: float) -> ConfidenceLevel:
    if score >= 0.85:
        return ConfidenceLevel.HIGH
    if score >= 0.60:
        return ConfidenceLevel.MEDIUM
    return ConfidenceLevel.LOW


class Protocol(BaseModel):
    """The canonical protocol record."""

    id: UUID = Field(default_factory=uuid4)
    slug: str  # URL-friendly identifier, e.g., "10x-chromium-3prime-v3"
    name: str
    version: str  # Protocol version (e.g., "v3.1")
    assay_family: AssayFamily
    molecule_type: MoleculeType
    description: str  # 2-3 sentence summary
    vendor: str | None = None
    platform: str | None = None  # e.g., "Illumina NovaSeq"
    chemistry_version: str | None = None
    compatible_instruments: list[str] = []
    custom_primer_required: bool | None = None
    strand_orientation_notes: str | None = None

    read_geometry: ReadGeometry
    adapters: list[Adapter] = []
    barcodes: list[BarcodeSpec] = []
    reagent_kits: list[ReagentKit] = []
    protocol_steps: list[str] = []  # High-level workflow steps
    protocol_timeline: list[ProtocolTimelineStep] = []
    qc_expectations: list[QCExpectation] = []
    failure_modes: list[FailureMode] = []
    caveats: list[str] = []
    library_structure: list[LibraryRegion] | None = None

    citations: list[Citation] = []
    source_urls: list[str] = []
    field_evidence: list[FieldEvidence] = []
    parser_config: dict | None = None

    confidence_score: float = Field(ge=0.0, le=1.0)
    review_status: ReviewStatus = ReviewStatus.PENDING
    extraction_notes: str | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    published_at: datetime | None = None
    schema_version: str = "1.0.0"

    @property
    def confidence_level(self) -> ConfidenceLevel:
        return _confidence_level(self.confidence_score)
