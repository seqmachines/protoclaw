from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator


class SeqSpecRegion(BaseModel):
    region_id: str
    region_type: str
    name: str | None = None
    sequence_type: str | None = None
    sequence: str | None = None
    min_len: int | None = None
    max_len: int | None = None
    onlist: str | None = None
    regions: list["SeqSpecRegion"] = Field(default_factory=list)


class SeqSpecRead(BaseModel):
    read_id: str
    name: str | None = None
    primer_id: str
    min_len: int | None = None
    max_len: int | None = None
    modality: str | None = None


class SeqSpec(BaseModel):
    """A seqspec-compatible assay description."""

    id: UUID = Field(default_factory=uuid4)
    assay_id: str
    name: str
    version: str | None = None
    doi: str | None = None
    date: str | None = None
    description: str
    modalities: list[str] = Field(default_factory=list)
    library_spec: list[SeqSpecRegion] = Field(default_factory=list)
    sequence_spec: list[SeqSpecRead] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)
    extraction_notes: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @model_validator(mode="after")
    def validate_primer_references(self) -> "SeqSpec":
        region_ids = {region.region_id for region in _flatten_regions(self.library_spec)}
        missing = [read.primer_id for read in self.sequence_spec if read.primer_id not in region_ids]
        if missing:
            raise ValueError(
                "sequence_spec primer_id values must reference region_ids in library_spec: "
                + ", ".join(sorted(set(missing)))
            )
        return self


def _flatten_regions(regions: list[SeqSpecRegion]) -> list[SeqSpecRegion]:
    flattened: list[SeqSpecRegion] = []
    for region in regions:
        flattened.append(region)
        flattened.extend(_flatten_regions(region.regions))
    return flattened


SeqSpecRegion.model_rebuild()
