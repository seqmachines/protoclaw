"""Parser agent tools for extracting protocol fields from source text."""

from pydantic import BaseModel, Field

from protocrawl.llm import glm5
from protocrawl.models.enums import (
    AssayFamily,
    MoleculeType,
    ReadType,
    SegmentRole,
)
from protocrawl.models.seqspec import SeqSpec, SeqSpecRead, SeqSpecRegion

# --- Response models for structured extraction ---


class ParsedMetadata(BaseModel):
    """Extracted protocol metadata."""

    name: str
    version: str | None = None
    assay_family: AssayFamily
    molecule_type: MoleculeType
    description: str
    vendor: str | None = None
    platform: str | None = None


class ParsedSegment(BaseModel):
    role: SegmentRole
    read_number: int
    start_pos: int
    length: int | None = None
    sequence: str | None = None
    description: str | None = None


class ParsedReadStructure(BaseModel):
    """Extracted read structure."""

    read_type: ReadType
    read1_length: int | None = None
    read2_length: int | None = None
    index1_length: int | None = None
    index2_length: int | None = None
    segments: list[ParsedSegment] = []


class ParsedBarcode(BaseModel):
    role: SegmentRole
    length: int
    whitelist_source: str | None = None
    addition_method: str | None = None


class ParsedBarcodes(BaseModel):
    """Extracted barcode specifications."""

    barcodes: list[ParsedBarcode] = []


class ParsedAdapter(BaseModel):
    name: str
    sequence: str
    position: str


class ParsedAdapters(BaseModel):
    """Extracted adapter sequences."""

    adapters: list[ParsedAdapter] = []


class ParsedReagent(BaseModel):
    name: str
    vendor: str
    catalog_number: str | None = None
    version: str | None = None


class ParsedReagents(BaseModel):
    """Extracted reagent kit information."""

    reagent_kits: list[ParsedReagent] = []


class ParsedProtocolDetails(BaseModel):
    """Extracted protocol steps, QC, failure modes, and caveats."""

    protocol_steps: list[str] = []
    qc_metrics: list[dict] = Field(
        default_factory=list,
        description="metric, typical_range_low, typical_range_high, notes",
    )
    failure_modes: list[dict] = Field(
        default_factory=list,
        description="Each dict has: description, symptom, likely_cause, mitigation",
    )
    caveats: list[str] = []


class ParsedSeqSpec(SeqSpec):
    """Structured seqspec-compatible document."""


# --- Tool functions ---

_EXTRACT_SYSTEM = (
    "You are an expert in sequencing library preparation and bioinformatics. "
    "Extract the requested information from the provided source text. "
    "Be precise and only include information explicitly stated in the text."
)


async def extract_metadata(source_text: str) -> ParsedMetadata:
    """Extract protocol metadata (name, assay type, vendor, etc.) from source text."""
    result = await glm5.extract_structured(
        prompt=(
            "Extract the sequencing protocol metadata from this document:\n\n"
            f"{source_text}"
        ),
        response_model=ParsedMetadata,
        system=_EXTRACT_SYSTEM,
    )
    return result


async def extract_read_structure(source_text: str) -> ParsedReadStructure:
    """Extract the complete read structure and segment layout from source text."""
    result = await glm5.extract_structured(
        prompt=(
            "Extract the sequencing read structure from this document. "
            "Include read type (paired-end or single-end), read lengths, "
            "and a detailed segment-by-segment layout specifying the role, "
            "read number (1=Read1, 2=Read2, 3=Index1, 4=Index2), "
            "0-based start position, length, and any fixed sequences "
            "for each contiguous region.\n\n"
            f"{source_text}"
        ),
        response_model=ParsedReadStructure,
        system=_EXTRACT_SYSTEM,
    )
    return result


async def extract_barcodes(source_text: str) -> ParsedBarcodes:
    """Extract barcode and UMI specifications from source text."""
    result = await glm5.extract_structured(
        prompt=(
            "Extract all barcode and UMI specifications from this document. "
            "For each barcode, include: role (cell_barcode, umi, sample_index, "
            "feature_barcode), length in bases, whitelist source file if "
            "mentioned, and addition method (ligation, PCR, template_switch, "
            "bead_synthesis, tagmentation, reverse_transcription, "
            "printed_on_slide, antibody_conjugation).\n\n"
            f"{source_text}"
        ),
        response_model=ParsedBarcodes,
        system=_EXTRACT_SYSTEM,
    )
    return result


async def extract_adapters(source_text: str) -> ParsedAdapters:
    """Extract adapter sequences from source text."""
    result = await glm5.extract_structured(
        prompt=(
            "Extract all adapter and primer sequences from this document. "
            "For each adapter, include: name, nucleotide sequence, and "
            "position (5prime, 3prime, or internal).\n\n"
            f"{source_text}"
        ),
        response_model=ParsedAdapters,
        system=_EXTRACT_SYSTEM,
    )
    return result


async def extract_reagents(source_text: str) -> ParsedReagents:
    """Extract reagent kit information from source text."""
    result = await glm5.extract_structured(
        prompt=(
            "Extract all reagent kit information from this document. "
            "Include: kit name, vendor/manufacturer, catalog number if "
            "available, and version if specified.\n\n"
            f"{source_text}"
        ),
        response_model=ParsedReagents,
        system=_EXTRACT_SYSTEM,
    )
    return result


async def extract_protocol_details(
    source_text: str,
) -> ParsedProtocolDetails:
    """Extract protocol steps, QC expectations, failure modes, and caveats."""
    result = await glm5.extract_structured(
        prompt=(
            "Extract the following from this sequencing protocol document:\n"
            "1. High-level protocol/workflow steps (not detailed bench protocol)\n"
            "2. QC metrics with typical expected ranges\n"
            "3. Common failure modes with symptoms, causes, and mitigations\n"
            "4. Important caveats or limitations\n\n"
            f"{source_text}"
        ),
        response_model=ParsedProtocolDetails,
        system=_EXTRACT_SYSTEM,
    )
    return result


_SEQSPEC_SYSTEM = (
    "You are an expert in sequencing assay specifications. "
    "Extract a seqspec-compatible assay description from the source text. "
    "Only include regions, reads, and metadata that are explicitly supported by the document. "
    "The output must obey seqspec conventions: top-level assay metadata, "
    "a nested 5prime-to-3prime library_spec, and sequence_spec reads keyed by primer_id "
    "that reference region_ids present in library_spec."
)


async def extract_seqspec(
    source_text: str,
    source_urls: list[str] | None = None,
) -> ParsedSeqSpec:
    """Extract a strict seqspec-style assay specification from source text."""
    prompt = (
        "Extract a seqspec-compatible sequencing assay specification from this source text.\n\n"
        "Requirements:\n"
        "- Use top-level fields: assay_id, name, version, doi, date, description, "
        "modalities, library_spec, sequence_spec, source_urls, extraction_notes.\n"
        "- library_spec must be a nested list of contiguous regions ordered 5prime to 3prime.\n"
        "- Each region must have a stable region_id and region_type.\n"
        "- sequence_spec must define reads using primer_id values that exactly match region_ids "
        "already present in library_spec.\n"
        "- Avoid inventing unsupported detail. Leave optional fields null when unknown.\n\n"
        f"Source text:\n{source_text}"
    )
    result = await glm5.extract_structured(
        prompt=prompt,
        response_model=ParsedSeqSpec,
        system=_SEQSPEC_SYSTEM,
    )
    if source_urls:
        result.source_urls = source_urls
    return result
