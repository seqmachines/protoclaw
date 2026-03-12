"""Normalizer agent tools for converting raw parsed data to canonical schema."""

import re

from protocrawl.models import (
    Adapter,
    BarcodeSpec,
    Citation,
    FailureMode,
    Protocol,
    QCExpectation,
    ReadGeometry,
    ReadSegment,
    ReagentKit,
)
from protocrawl.models.enums import (
    AssayFamily,
    MoleculeType,
    ReadType,
    SegmentRole,
)
from protocrawl.models.seqspec import SeqSpec, SeqSpecRegion


def _slugify(name: str, version: str | None = None) -> str:
    """Generate a URL-friendly slug from protocol name and version."""
    text = name.lower()
    if version:
        text = f"{text}-{version.lower()}"
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def _check_segment_consistency(
    segments: list[dict],
    read1_length: int | None,
    read2_length: int | None,
) -> list[str]:
    """Check that segments fit within declared read lengths."""
    issues = []
    for read_num, declared_len in [(1, read1_length), (2, read2_length)]:
        if declared_len is None:
            continue
        read_segments = [s for s in segments if s.get("read_number") == read_num]
        total = sum(s.get("length") or 0 for s in read_segments)
        if total > 0 and total > declared_len:
            issues.append(
                f"Read {read_num} segments total {total}bp "
                f"but declared length is {declared_len}bp"
            )
    return issues


def _check_barcode_segment_match(
    segments: list[dict],
    barcodes: list[dict],
) -> list[str]:
    """Check that barcode specs have matching read segments."""
    issues = []
    segment_roles = {s.get("role") for s in segments}
    for bc in barcodes:
        role = bc.get("role")
        if role and role not in segment_roles and role != "umi":
            issues.append(
                f"Barcode spec with role '{role}' has no matching read segment"
            )
    return issues


_FAMILY_MOLECULE_MAP = {
    AssayFamily.SCRNA_SEQ: {MoleculeType.RNA},
    AssayFamily.SCATAC_SEQ: {MoleculeType.CHROMATIN, MoleculeType.DNA},
    AssayFamily.SPATIAL_TRANSCRIPTOMICS: {MoleculeType.RNA},
    AssayFamily.BULK_RNA_SEQ: {MoleculeType.RNA},
    AssayFamily.METHYLATION: {MoleculeType.DNA},
    AssayFamily.MULTIOME: {MoleculeType.MULTI},
    AssayFamily.CITE_SEQ: {MoleculeType.MULTI, MoleculeType.PROTEIN},
}


def compute_confidence(
    *,
    metadata: dict | None = None,
    read_structure: dict | None = None,
    barcodes: list[dict] | None = None,
    adapters: list[dict] | None = None,
    citations: list[dict] | None = None,
    protocol_details: dict | None = None,
) -> dict:
    """Compute a confidence score and list of issues for parsed protocol data.

    Returns:
        dict with keys: score (float), level (str), issues (list[str]),
        notes (str)
    """
    score = 0.0
    issues: list[str] = []

    # Metadata completeness (up to 0.25)
    if metadata:
        has_name = bool(metadata.get("name"))
        has_family = bool(metadata.get("assay_family"))
        has_description = bool(metadata.get("description"))
        meta_score = sum([has_name, has_family, has_description]) / 3
        score += 0.25 * meta_score
        if not has_name:
            issues.append("Missing protocol name")
        if not has_family:
            issues.append("Missing assay family")
    else:
        issues.append("No metadata extracted")

    # Read structure (up to 0.30)
    if read_structure:
        has_type = bool(read_structure.get("read_type"))
        segments = read_structure.get("segments", [])
        has_segments = len(segments) > 0
        rs_score = (0.5 if has_type else 0) + (0.5 if has_segments else 0)
        score += 0.30 * rs_score

        if has_segments:
            seg_issues = _check_segment_consistency(
                segments,
                read_structure.get("read1_length"),
                read_structure.get("read2_length"),
            )
            issues.extend(seg_issues)
        else:
            issues.append("No read segments extracted")
    else:
        issues.append("No read structure extracted")

    # Barcodes (up to 0.15)
    if barcodes and len(barcodes) > 0:
        score += 0.15
        if read_structure:
            bc_issues = _check_barcode_segment_match(
                read_structure.get("segments", []), barcodes
            )
            issues.extend(bc_issues)
    else:
        issues.append("No barcodes extracted")

    # Citations (up to 0.15)
    if citations and len(citations) > 0:
        has_doi = any(c.get("doi") for c in citations)
        score += 0.15 if has_doi else 0.10
    else:
        issues.append("No citations found")

    # Protocol details (up to 0.15)
    if protocol_details:
        has_steps = len(protocol_details.get("protocol_steps", [])) > 0
        has_qc = len(protocol_details.get("qc_metrics", [])) > 0
        detail_score = sum([has_steps, has_qc]) / 2
        score += 0.15 * detail_score
    else:
        issues.append("No protocol details extracted")

    # Assay-molecule consistency check
    if metadata:
        try:
            family = AssayFamily(metadata.get("assay_family", ""))
            mol = MoleculeType(metadata.get("molecule_type", ""))
            valid_mols = _FAMILY_MOLECULE_MAP.get(family)
            if valid_mols and mol not in valid_mols:
                issues.append(
                    f"Assay family '{family}' typically uses "
                    f"{valid_mols}, but got '{mol}'"
                )
                score -= 0.05
        except ValueError:
            pass

    score = max(0.0, min(1.0, round(score, 2)))

    if score >= 0.85:
        level = "high"
    elif score >= 0.60:
        level = "medium"
    else:
        level = "low"

    return {
        "score": score,
        "level": level,
        "issues": issues,
        "notes": f"{len(issues)} issue(s) found" if issues else "Clean extraction",
    }


def normalize_to_schema(
    *,
    metadata: dict | None = None,
    read_structure: dict | None = None,
    barcodes: list[dict] | None = None,
    adapters: list[dict] | None = None,
    reagents: list[dict] | None = None,
    citations: list[dict] | None = None,
    protocol_details: dict | None = None,
    source_urls: list[str] | None = None,
) -> Protocol:
    """Assemble parsed components into a canonical Protocol model.

    Takes the raw outputs from each parser tool and combines them
    into a validated Protocol instance.

    Returns:
        Dict representation of the canonical Protocol.
    """
    meta = metadata or {}
    name = meta.get("name", "Unknown Protocol")
    version = meta.get("version")

    # Build read geometry
    rs = read_structure or {}
    geometry = ReadGeometry(
        read_type=ReadType(rs.get("read_type", "paired-end")),
        read1_length=rs.get("read1_length"),
        read2_length=rs.get("read2_length"),
        index1_length=rs.get("index1_length"),
        index2_length=rs.get("index2_length"),
        segments=[
            ReadSegment(
                role=SegmentRole(s["role"]),
                read_number=s["read_number"],
                start_pos=s["start_pos"],
                length=s.get("length"),
                sequence=s.get("sequence"),
                description=s.get("description"),
            )
            for s in rs.get("segments", [])
        ],
    )

    # Build barcode specs
    bc_list = [
        BarcodeSpec(
            role=SegmentRole(b["role"]),
            length=b["length"],
            whitelist_source=b.get("whitelist_source"),
            addition_method=b.get("addition_method"),
        )
        for b in (barcodes or [])
    ]

    # Build adapters
    adapter_list = [
        Adapter(
            name=a["name"],
            sequence=a["sequence"],
            position=a["position"],
        )
        for a in (adapters or [])
    ]

    # Build reagent kits
    reagent_list = [
        ReagentKit(
            name=r["name"],
            vendor=r["vendor"],
            catalog_number=r.get("catalog_number"),
            version=r.get("version"),
        )
        for r in (reagents or [])
    ]

    # Build citations
    citation_list = [
        Citation(
            doi=c.get("doi"),
            pmid=c.get("pmid"),
            arxiv_id=c.get("arxiv_id"),
            title=c.get("title", ""),
            authors=c.get("authors", []),
            year=c.get("year"),
            url=c.get("url"),
        )
        for c in (citations or [])
    ]

    # Protocol details
    details = protocol_details or {}
    qc_list = [
        QCExpectation(
            metric=q["metric"],
            typical_range_low=q.get("typical_range_low"),
            typical_range_high=q.get("typical_range_high"),
            notes=q.get("notes"),
        )
        for q in details.get("qc_metrics", [])
    ]
    fm_list = [
        FailureMode(
            description=f["description"],
            symptom=f["symptom"],
            likely_cause=f["likely_cause"],
            mitigation=f.get("mitigation"),
        )
        for f in details.get("failure_modes", [])
    ]

    # Compute confidence
    confidence = compute_confidence(
        metadata=metadata,
        read_structure=read_structure,
        barcodes=barcodes,
        adapters=adapters,
        citations=citations,
        protocol_details=protocol_details,
    )

    protocol = Protocol(
        slug=_slugify(name, version),
        name=name,
        version=version or "v1",
        assay_family=AssayFamily(meta.get("assay_family", "other")),
        molecule_type=MoleculeType(meta.get("molecule_type", "RNA")),
        description=meta.get("description", ""),
        vendor=meta.get("vendor"),
        platform=meta.get("platform"),
        read_geometry=geometry,
        adapters=adapter_list,
        barcodes=bc_list,
        reagent_kits=reagent_list,
        protocol_steps=details.get("protocol_steps", []),
        qc_expectations=qc_list,
        failure_modes=fm_list,
        caveats=details.get("caveats", []),
        citations=citation_list,
        source_urls=source_urls or [],
        confidence_score=confidence["score"],
        extraction_notes=confidence["notes"],
    )
    return protocol


def _seqspec_region_length(region: SeqSpecRegion) -> int | None:
    if region.max_len is not None:
        return region.max_len
    if region.min_len is not None and region.max_len is None:
        return region.min_len
    if region.sequence:
        return len(region.sequence)
    return None


def _seqspec_paths(regions: list[SeqSpecRegion]) -> list[list[SeqSpecRegion]]:
    paths: list[list[SeqSpecRegion]] = []
    for region in regions:
        child_paths = _seqspec_paths(region.regions)
        if not child_paths:
            paths.append([region])
            continue
        for path in child_paths:
            paths.append([region, *path])
    return paths


def _segment_role_from_region_type(region_type: str) -> SegmentRole:
    normalized = region_type.lower()
    mapping = {
        "barcode": SegmentRole.CELL_BARCODE,
        "umi": SegmentRole.UMI,
        "cdna": SegmentRole.CDNA,
        "gdna": SegmentRole.GENOMIC_INSERT,
        "index": SegmentRole.SAMPLE_INDEX,
        "adapter": SegmentRole.ADAPTER,
        "primer": SegmentRole.PRIMER,
        "linker": SegmentRole.LINKER,
        "spacer": SegmentRole.SPACER,
        "feature_barcode": SegmentRole.FEATURE_BARCODE,
    }
    return mapping.get(normalized, SegmentRole.OTHER)


def _assay_family_from_seqspec(seqspec: SeqSpec) -> AssayFamily:
    haystack = " ".join([seqspec.name, seqspec.description, *seqspec.modalities]).lower()
    if "atac" in haystack:
        return AssayFamily.SCATAC_SEQ
    if "spatial" in haystack or "visium" in haystack or "xenium" in haystack:
        return AssayFamily.SPATIAL_TRANSCRIPTOMICS
    if "multiome" in haystack:
        return AssayFamily.MULTIOME
    if "cite" in haystack or "protein" in haystack:
        return AssayFamily.CITE_SEQ
    if "bulk" in haystack:
        return AssayFamily.BULK_RNA_SEQ
    return AssayFamily.SCRNA_SEQ


def _molecule_type_from_seqspec(seqspec: SeqSpec) -> MoleculeType:
    haystack = " ".join(seqspec.modalities).lower()
    if "chromatin" in haystack or "atac" in haystack or "dna" in haystack:
        return MoleculeType.CHROMATIN
    if "protein" in haystack:
        return MoleculeType.PROTEIN
    return MoleculeType.RNA


def seqspec_confidence(seqspec: SeqSpec) -> dict:
    score = 0.0
    issues: list[str] = []

    if seqspec.name and seqspec.assay_id:
        score += 0.25
    else:
        issues.append("Missing assay_id or name")

    if seqspec.library_spec:
        score += 0.35
    else:
        issues.append("Missing library_spec")

    if seqspec.sequence_spec:
        score += 0.30
    else:
        issues.append("Missing sequence_spec")

    if seqspec.modalities:
        score += 0.10
    else:
        issues.append("Missing modalities")

    return {
        "score": round(min(score, 1.0), 2),
        "notes": f"{len(issues)} seqspec issue(s) found" if issues else "Clean seqspec extraction",
        "issues": issues,
    }


def seqspec_to_protocol(seqspec: SeqSpec) -> Protocol:
    paths = _seqspec_paths(seqspec.library_spec)
    read_segments: list[ReadSegment] = []
    read_lengths: dict[int, int | None] = {}

    for index, read in enumerate(seqspec.sequence_spec, start=1):
        path = next((path for path in paths if any(region.region_id == read.primer_id for region in path)), [])
        if path:
            primer_index = next(
                i for i, region in enumerate(path) if region.region_id == read.primer_id
            )
            relevant_regions = path[primer_index:]
        else:
            relevant_regions = []

        cursor = 0
        for region in relevant_regions:
            length = _seqspec_region_length(region)
            read_segments.append(
                ReadSegment(
                    role=_segment_role_from_region_type(region.region_type),
                    read_number=index,
                    start_pos=cursor,
                    length=length,
                    sequence=region.sequence,
                    description=region.name or region.region_id,
                )
            )
            if length is not None:
                cursor += length
        read_lengths[index] = read.max_len or (cursor if cursor > 0 else None)

    flattened_regions = [region for path in paths for region in path]
    barcodes = [
        BarcodeSpec(
            role=_segment_role_from_region_type(region.region_type),
            length=_seqspec_region_length(region) or 0,
            whitelist_source=region.onlist,
        )
        for region in flattened_regions
        if region.region_type.lower() in {"barcode", "umi", "index", "feature_barcode"}
        and (_seqspec_region_length(region) or 0) > 0
    ]

    adapters = [
        Adapter(
            name=region.name or region.region_id,
            sequence=region.sequence or "",
            position="internal",
        )
        for region in flattened_regions
        if region.region_type.lower() == "adapter" and region.sequence
    ]

    confidence = seqspec_confidence(seqspec)
    read_type = ReadType.PAIRED_END if len(seqspec.sequence_spec) > 1 else ReadType.SINGLE_END

    return Protocol(
        slug=_slugify(seqspec.assay_id, seqspec.version),
        name=seqspec.name,
        version=seqspec.version or "v1",
        assay_family=_assay_family_from_seqspec(seqspec),
        molecule_type=_molecule_type_from_seqspec(seqspec),
        description=seqspec.description,
        read_geometry=ReadGeometry(
            read_type=read_type,
            read1_length=read_lengths.get(1),
            read2_length=read_lengths.get(2),
            index1_length=read_lengths.get(3),
            index2_length=read_lengths.get(4),
            segments=read_segments,
        ),
        adapters=adapters,
        barcodes=barcodes,
        reagent_kits=[],
        protocol_steps=[],
        citations=[],
        source_urls=seqspec.source_urls,
        confidence_score=confidence["score"],
        extraction_notes=seqspec.extraction_notes or confidence["notes"],
    )
