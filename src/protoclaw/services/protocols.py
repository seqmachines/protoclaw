from __future__ import annotations

import re

from protoclaw.db.tables import ProtocolRow
from protoclaw.models import (
    Adapter,
    BarcodeSpec,
    Citation,
    ExportArtifact,
    ExplorerPreprocessingGroup,
    ExplorerReadTrace,
    ExplorerSegment,
    ExplorerSegmentReadMapping,
    FailureMode,
    FieldEvidence,
    LibraryRegion,
    Protocol,
    ProtocolExplorer,
    ProtocolExplorerHeader,
    ProtocolTimelineStep,
    QCExpectation,
    ReadGeometry,
    ReadSegment,
    ReagentKit,
    SeqSpec,
    SeqSpecRead,
    SeqSpecRegion,
    SequencingRecipe,
)
from protoclaw.models.enums import (
    AssayFamily,
    MoleculeType,
    ReadType,
    ReviewStatus,
    SegmentRole,
)


_READ_LABELS = {
    1: ("R1", "Read 1"),
    2: ("R2", "Read 2"),
    3: ("I1", "Index 1"),
    4: ("I2", "Index 2"),
}


_ROLE_LABELS = {
    SegmentRole.CELL_BARCODE: "Cell barcode",
    SegmentRole.UMI: "UMI",
    SegmentRole.CDNA: "Insert",
    SegmentRole.SAMPLE_INDEX: "Sample index",
    SegmentRole.LINKER: "Linker",
    SegmentRole.SPACER: "Spacer",
    SegmentRole.PRIMER: "Primer",
    SegmentRole.ADAPTER: "Adapter",
    SegmentRole.FEATURE_BARCODE: "Feature barcode",
    SegmentRole.GENOMIC_INSERT: "Insert",
    SegmentRole.OTHER: "Other",
}


_LIBRARY_TYPE_ROLE_MAP = {
    "cbc": SegmentRole.CELL_BARCODE,
    "cell_barcode": SegmentRole.CELL_BARCODE,
    "umi": SegmentRole.UMI,
    "cdna": SegmentRole.CDNA,
    "insert": SegmentRole.CDNA,
    "genomic_insert": SegmentRole.GENOMIC_INSERT,
    "index": SegmentRole.SAMPLE_INDEX,
    "i7": SegmentRole.SAMPLE_INDEX,
    "i5": SegmentRole.SAMPLE_INDEX,
    "linker": SegmentRole.LINKER,
    "primer": SegmentRole.PRIMER,
    "r1_primer": SegmentRole.PRIMER,
    "r2_primer": SegmentRole.PRIMER,
    "adapter": SegmentRole.ADAPTER,
    "p5": SegmentRole.ADAPTER,
    "p7": SegmentRole.ADAPTER,
}


def row_to_protocol(row: ProtocolRow) -> Protocol:
    return Protocol(
        id=row.id,
        slug=row.slug,
        name=row.name,
        version=row.version,
        assay_family=AssayFamily(row.assay_family),
        molecule_type=MoleculeType(row.molecule_type),
        description=row.description,
        vendor=row.vendor,
        platform=row.platform,
        chemistry_version=getattr(row, "chemistry_version", None),
        compatible_instruments=getattr(row, "compatible_instruments", None) or [],
        custom_primer_required=getattr(row, "custom_primer_required", None),
        strand_orientation_notes=getattr(row, "strand_orientation_notes", None),
        read_geometry=ReadGeometry(
            read_type=ReadType(row.read_type),
            read1_length=row.read1_length,
            read2_length=row.read2_length,
            index1_length=row.index1_length,
            index2_length=row.index2_length,
            segments=[
                ReadSegment(
                    role=SegmentRole(s.role),
                    read_number=s.read_number,
                    start_pos=s.start_pos,
                    length=s.length,
                    sequence=s.sequence,
                    description=s.description,
                )
                for s in row.read_segments
            ],
        ),
        adapters=[
            Adapter(name=a.name, sequence=a.sequence, position=a.position)
            for a in row.adapters
        ],
        barcodes=[
            BarcodeSpec(
                role=SegmentRole(b.role),
                length=b.length,
                whitelist_source=b.whitelist_source,
                addition_method=b.addition_method,
            )
            for b in row.barcodes
        ],
        reagent_kits=[
            ReagentKit(
                name=r.name,
                vendor=r.vendor,
                catalog_number=r.catalog_number,
                version=r.version,
            )
            for r in row.reagent_kits
        ],
        citations=[
            Citation(
                doi=c.doi,
                pmid=c.pmid,
                arxiv_id=c.arxiv_id,
                title=c.title,
                authors=c.authors,
                year=c.year,
                url=c.url,
            )
            for c in row.citations
        ],
        qc_expectations=[
            QCExpectation(
                metric=q.metric,
                typical_range_low=q.typical_range_low,
                typical_range_high=q.typical_range_high,
                notes=q.notes,
            )
            for q in row.qc_expectations
        ],
        failure_modes=[
            FailureMode(
                description=f.description,
                symptom=f.symptom,
                likely_cause=f.likely_cause,
                mitigation=f.mitigation,
            )
            for f in row.failure_modes
        ],
        protocol_steps=row.protocol_steps,
        protocol_timeline=[
            ProtocolTimelineStep(**step)
            for step in (getattr(row, "protocol_timeline", None) or [])
        ],
        caveats=row.caveats,
        library_structure=[
            LibraryRegion(**r) for r in (row.library_structure or [])
        ] or None,
        source_urls=row.source_urls,
        field_evidence=[
            FieldEvidence(**e)
            for e in (getattr(row, "field_evidence", None) or [])
        ],
        parser_config=getattr(row, "parser_config", None),
        confidence_score=row.confidence_score,
        review_status=ReviewStatus(row.review_status),
        extraction_notes=row.extraction_notes,
        created_at=row.created_at,
        updated_at=row.updated_at,
        published_at=row.published_at,
        schema_version=row.schema_version,
    )


def protocol_to_explorer(protocol: Protocol) -> ProtocolExplorer:
    timeline = _timeline_for_protocol(protocol)
    blueprint_segments = _blueprint_segments(protocol, timeline)
    header = ProtocolExplorerHeader(
        assay_name=protocol.name,
        chemistry_version=protocol.chemistry_version or protocol.version,
        assay_family=protocol.assay_family,
        vendor=protocol.vendor,
        compatible_instruments=protocol.compatible_instruments
        or ([protocol.platform] if protocol.platform else []),
        confidence_score=protocol.confidence_score,
        review_status=protocol.review_status,
        source_links=protocol.source_urls,
        last_updated=protocol.updated_at,
        revision=protocol.schema_version,
    )
    recipe = SequencingRecipe(
        read1_length=protocol.read_geometry.read1_length,
        read2_length=protocol.read_geometry.read2_length,
        index1_length=protocol.read_geometry.index1_length,
        index2_length=protocol.read_geometry.index2_length,
        custom_primer_required=protocol.custom_primer_required,
        supported_instruments=protocol.compatible_instruments
        or ([protocol.platform] if protocol.platform else []),
        orientation_notes=protocol.strand_orientation_notes,
        read_structure_string=_read_structure_string(protocol),
    )
    exports = [
        ExportArtifact(
            export_id="seqspec-json",
            label="seqspec JSON",
            format="json",
            href=f"/protocols/{protocol.slug}/seqspec?format=json",
        ),
        ExportArtifact(
            export_id="seqspec-yaml",
            label="seqspec YAML",
            format="yaml",
            href=f"/protocols/{protocol.slug}/seqspec?format=yaml",
        ),
        ExportArtifact(
            export_id="parser-config",
            label="Parser config",
            format="json",
            href=f"/protocols/{protocol.slug}/exports/parser-config",
        ),
        ExportArtifact(
            export_id="tsv-summary",
            label="TSV summary",
            format="tsv",
            href=f"/protocols/{protocol.slug}/exports/tsv",
        ),
        ExportArtifact(
            export_id="read-structure",
            label="Read structure",
            format="text",
            copy_text=_read_structure_string(protocol),
        ),
    ]
    evidence = protocol.field_evidence or _fallback_evidence(protocol, blueprint_segments)
    return ProtocolExplorer(
        header=header,
        blueprint_segments=blueprint_segments,
        sequencer_reads=_sequencer_reads(protocol),
        preprocessing_groups=_preprocessing_groups(blueprint_segments),
        timeline=timeline,
        recipe=recipe,
        evidence=evidence,
        exports=exports,
        citations=protocol.citations,
        description=protocol.description,
        extraction_notes=protocol.extraction_notes,
    )


def protocol_tsv_summary(protocol: Protocol) -> str:
    rows = [
        ("slug", protocol.slug),
        ("name", protocol.name),
        ("version", protocol.version),
        ("chemistry_version", protocol.chemistry_version or protocol.version),
        ("assay_family", protocol.assay_family.value),
        ("molecule_type", protocol.molecule_type.value),
        ("vendor", protocol.vendor or ""),
        ("platform", protocol.platform or ""),
        ("compatible_instruments", ";".join(protocol.compatible_instruments)),
        ("read_structure", _read_structure_string(protocol)),
        ("custom_primer_required", "" if protocol.custom_primer_required is None else str(protocol.custom_primer_required).lower()),
        ("orientation_notes", protocol.strand_orientation_notes or ""),
        ("confidence_score", str(protocol.confidence_score)),
        ("review_status", protocol.review_status.value),
    ]
    return "field\tvalue\n" + "\n".join(f"{field}\t{value}" for field, value in rows)


def protocol_to_seqspec(protocol: Protocol) -> SeqSpec:
    if protocol.library_structure:
        regions = [
            SeqSpecRegion(
                region_id=f"region-{index}",
                region_type=_seqspec_region_type(region.type),
                name=region.label or _humanize(region.type),
                sequence=region.top.replace(".", ""),
                min_len=len(region.top.replace(".", "")) or None,
                max_len=len(region.top.replace(".", "")) or None,
            )
            for index, region in enumerate(protocol.library_structure, start=1)
        ]
    else:
        regions = [
            SeqSpecRegion(
                region_id=f"region-{index}",
                region_type=_seqspec_region_type(segment.role.value),
                name=segment.description or _ROLE_LABELS.get(segment.role, _humanize(segment.role.value)),
                sequence=segment.sequence,
                min_len=segment.length,
                max_len=segment.length,
            )
            for index, segment in enumerate(
                sorted(protocol.read_geometry.segments, key=lambda item: (item.read_number, item.start_pos)),
                start=1,
            )
        ]

    grouped_regions: dict[int, list[SeqSpecRegion]] = {}
    if protocol.read_geometry.segments:
        ordered_segments = sorted(protocol.read_geometry.segments, key=lambda item: (item.read_number, item.start_pos))
        for index, segment in enumerate(ordered_segments, start=1):
            grouped_regions.setdefault(segment.read_number, []).append(regions[index - 1])

    sequence_spec = []
    read_lengths = {
        1: protocol.read_geometry.read1_length,
        2: protocol.read_geometry.read2_length,
        3: protocol.read_geometry.index1_length,
        4: protocol.read_geometry.index2_length,
    }
    for read_number in sorted(grouped_regions):
        read_key, label = _READ_LABELS.get(read_number, (f"R{read_number}", f"Read {read_number}"))
        primer_id = grouped_regions[read_number][0].region_id
        sequence_spec.append(
            SeqSpecRead(
                read_id=read_key.lower(),
                name=label,
                primer_id=primer_id,
                min_len=read_lengths.get(read_number),
                max_len=read_lengths.get(read_number),
                modality=protocol.assay_family.value,
            )
        )

    return SeqSpec(
        assay_id=protocol.slug,
        name=protocol.name,
        version=protocol.chemistry_version or protocol.version,
        description=protocol.description,
        modalities=[protocol.assay_family.value, protocol.molecule_type.value],
        library_spec=regions,
        sequence_spec=sequence_spec,
        source_urls=protocol.source_urls,
        extraction_notes=protocol.extraction_notes,
    )


def _timeline_for_protocol(protocol: Protocol) -> list[ProtocolTimelineStep]:
    if protocol.protocol_timeline:
        return protocol.protocol_timeline
    timeline: list[ProtocolTimelineStep] = []
    for index, step in enumerate(protocol.protocol_steps, start=1):
        timeline.append(
            ProtocolTimelineStep(
                step_id=f"step-{index}",
                title=step,
                summary=None,
            )
        )
    return timeline


def _blueprint_segments(
    protocol: Protocol, timeline: list[ProtocolTimelineStep]
) -> list[ExplorerSegment]:
    if protocol.library_structure:
        segments = _segments_from_library_structure(protocol.library_structure)
    else:
        segments = _segments_from_read_geometry(protocol)

    introductions: dict[str, str] = {}
    modifications: dict[str, list[str]] = {}
    for step in timeline:
        for segment_id in step.introduced_segment_ids:
            introductions.setdefault(segment_id, step.step_id)
        for segment_id in step.modified_segment_ids:
            modifications.setdefault(segment_id, []).append(step.step_id)

    return [
        segment.model_copy(
            update={
                "introduced_by_step_id": introductions.get(segment.segment_id),
                "modified_by_step_ids": modifications.get(segment.segment_id, []),
            }
        )
        for segment in segments
    ]


def _segments_from_library_structure(
    regions: list[LibraryRegion],
) -> list[ExplorerSegment]:
    segments: list[ExplorerSegment] = []
    for index, region in enumerate(regions, start=1):
        kind = region.type.lower()
        role = _LIBRARY_TYPE_ROLE_MAP.get(kind)
        sequence = region.top.replace(".", "")
        length = len(sequence) if sequence else None
        segment_id = f"seg-{index}-{_slug_token(region.label or kind)}"
        segments.append(
            ExplorerSegment(
                segment_id=segment_id,
                label=region.label or _humanize(kind),
                kind=kind,
                role=role,
                sequence=region.top,
                length=length,
                description=f"{region.label or _humanize(kind)} segment",
                preprocessing_group=_preprocessing_group_for_segment(role, kind),
                read_mappings=_read_mappings_for_segment(kind, role),
            )
        )
    return segments


def _segments_from_read_geometry(protocol: Protocol) -> list[ExplorerSegment]:
    segments: list[ExplorerSegment] = []
    for index, read_segment in enumerate(
        sorted(protocol.read_geometry.segments, key=lambda segment: (segment.read_number, segment.start_pos)),
        start=1,
    ):
        label = read_segment.description or _ROLE_LABELS.get(read_segment.role, _humanize(read_segment.role.value))
        read_key, read_label = _READ_LABELS.get(read_segment.read_number, (f"R{read_segment.read_number}", f"Read {read_segment.read_number}"))
        segment_id = f"read-seg-{index}"
        length = read_segment.length
        end_cycle = read_segment.start_pos + (length or 1)
        segments.append(
            ExplorerSegment(
                segment_id=segment_id,
                label=label,
                kind=read_segment.role.value,
                role=read_segment.role,
                sequence=read_segment.sequence,
                length=length,
                description=f"{label} in {read_label}",
                preprocessing_group=_preprocessing_group_for_segment(read_segment.role, read_segment.role.value),
                read_mappings=[
                    ExplorerSegmentReadMapping(
                        read_key=read_key,
                        label=read_label,
                        start_cycle=read_segment.start_pos + 1,
                        end_cycle=end_cycle,
                    )
                ],
            )
        )
    return segments


def _read_mappings_for_segment(
    kind: str, role: SegmentRole | None
) -> list[ExplorerSegmentReadMapping]:
    mappings: list[ExplorerSegmentReadMapping] = []
    if role in {SegmentRole.CELL_BARCODE, SegmentRole.UMI}:
        mappings.append(
            ExplorerSegmentReadMapping(
                read_key="R1",
                label="Read 1",
                start_cycle=1,
                end_cycle=1,
            )
        )
    elif role in {SegmentRole.CDNA, SegmentRole.GENOMIC_INSERT}:
        mappings.append(
            ExplorerSegmentReadMapping(
                read_key="R2",
                label="Read 2",
                start_cycle=1,
                end_cycle=1,
            )
        )
    elif kind in {"i7", "index"}:
        mappings.append(
            ExplorerSegmentReadMapping(
                read_key="I1",
                label="Index 1",
                start_cycle=1,
                end_cycle=1,
            )
        )
    elif kind == "i5":
        mappings.append(
            ExplorerSegmentReadMapping(
                read_key="I2",
                label="Index 2",
                start_cycle=1,
                end_cycle=1,
            )
        )
    return mappings


def _sequencer_reads(protocol: Protocol) -> list[ExplorerReadTrace]:
    grouped: dict[int, list[ReadSegment]] = {}
    for segment in protocol.read_geometry.segments:
        grouped.setdefault(segment.read_number, []).append(segment)

    read_lengths = {
        1: protocol.read_geometry.read1_length,
        2: protocol.read_geometry.read2_length,
        3: protocol.read_geometry.index1_length,
        4: protocol.read_geometry.index2_length,
    }
    traces: list[ExplorerReadTrace] = []
    for read_number in sorted(grouped):
        read_key, label = _READ_LABELS.get(read_number, (f"R{read_number}", f"Read {read_number}"))
        segments = [
            f"{_ROLE_LABELS.get(segment.role, _humanize(segment.role.value))}"
            f" ({segment.start_pos + 1}-{segment.start_pos + (segment.length or 1)})"
            for segment in sorted(grouped[read_number], key=lambda item: item.start_pos)
        ]
        traces.append(
            ExplorerReadTrace(
                read_key=read_key,
                label=label,
                length=read_lengths.get(read_number),
                segments=segments,
            )
        )
    return traces


def _preprocessing_groups(
    segments: list[ExplorerSegment],
) -> list[ExplorerPreprocessingGroup]:
    grouped: dict[str, list[str]] = {}
    descriptions = {
        "barcode": "Segments used to identify cells, samples, or features.",
        "umi": "Random bases collapsed during molecule counting.",
        "insert": "Biological sequence retained for alignment or quantification.",
        "library": "Adapters, primers, and structural anchors needed for sequencing.",
    }
    labels = {
        "barcode": "Barcode extraction",
        "umi": "UMI extraction",
        "insert": "Insert alignment",
        "library": "Library anchors",
    }
    for segment in segments:
        if not segment.preprocessing_group:
            continue
        grouped.setdefault(segment.preprocessing_group, []).append(segment.segment_id)
    return [
        ExplorerPreprocessingGroup(
            group_id=group_id,
            label=labels[group_id],
            description=descriptions[group_id],
            segment_ids=segment_ids,
        )
        for group_id, segment_ids in grouped.items()
    ]


def _preprocessing_group_for_segment(
    role: SegmentRole | None, kind: str
) -> str | None:
    if role in {SegmentRole.CELL_BARCODE, SegmentRole.SAMPLE_INDEX, SegmentRole.FEATURE_BARCODE}:
        return "barcode"
    if role == SegmentRole.UMI:
        return "umi"
    if role in {SegmentRole.CDNA, SegmentRole.GENOMIC_INSERT} or kind in {"insert", "poly_dt", "poly_a"}:
        return "insert"
    if role in {SegmentRole.ADAPTER, SegmentRole.PRIMER, SegmentRole.LINKER, SegmentRole.SPACER}:
        return "library"
    if kind in {"p5", "p7", "r1_primer", "r2_primer"}:
        return "library"
    return None


def _read_structure_string(protocol: Protocol) -> str:
    parts = []
    grouped: dict[int, list[ReadSegment]] = {}
    for segment in protocol.read_geometry.segments:
        grouped.setdefault(segment.read_number, []).append(segment)
    for read_number in sorted(grouped):
        read_key, _ = _READ_LABELS.get(read_number, (f"R{read_number}", f"Read {read_number}"))
        tokens = []
        for segment in sorted(grouped[read_number], key=lambda item: item.start_pos):
            label = _ROLE_LABELS.get(segment.role, _humanize(segment.role.value))
            length = "var" if segment.length is None else str(segment.length)
            tokens.append(f"{label}:{length}")
        parts.append(f"{read_key}[{', '.join(tokens)}]")
    return " | ".join(parts)


def _fallback_evidence(
    protocol: Protocol, blueprint_segments: list[ExplorerSegment]
) -> list[FieldEvidence]:
    evidence: list[FieldEvidence] = []
    source_url = protocol.source_urls[0] if protocol.source_urls else None
    evidence.append(
        FieldEvidence(
            field_path="name",
            label="Assay name",
            value=protocol.name,
            source_url=source_url,
            extraction_mode="inferred",
            confidence_score=protocol.confidence_score,
            parser_stage="serialization",
            parser_source="protocol_to_explorer",
            notes="Derived from the canonical protocol record because no field-level evidence is stored.",
        )
    )
    for segment in blueprint_segments:
        evidence.append(
            FieldEvidence(
                field_path=f"segment.{segment.segment_id}",
                label=segment.label,
                value=segment.sequence or (f"{segment.length} nt" if segment.length else segment.kind),
                segment_id=segment.segment_id,
                source_url=source_url,
                extraction_mode="inferred",
                confidence_score=max(protocol.confidence_score - 0.1, 0.0),
                parser_stage="serialization",
                parser_source="protocol_to_explorer",
                notes="Segment metadata was derived from stored read geometry, adapters, and library structure.",
            )
        )
    return evidence


def _seqspec_region_type(value: str) -> str:
    normalized = value.lower()
    if normalized in {"cbc", "cell_barcode", "sample_index", "index", "i7", "i5"}:
        return "barcode"
    if normalized in {"umi"}:
        return "umi"
    if normalized in {"cdna", "insert", "genomic_insert"}:
        return "cdna"
    if normalized in {"p5", "p7", "adapter"}:
        return "adapter"
    if normalized in {"r1_primer", "r2_primer", "primer"}:
        return "primer"
    return normalized


def _slug_token(value: str) -> str:
    token = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return token or "segment"


def _humanize(value: str) -> str:
    return value.replace("_", " ").replace("-", " ").title()
