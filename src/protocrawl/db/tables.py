import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class ProtocolRow(Base):
    __tablename__ = "protocols"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(500))
    version: Mapped[str] = mapped_column(String(50))
    assay_family: Mapped[str] = mapped_column(String(100))
    molecule_type: Mapped[str] = mapped_column(String(50))
    description: Mapped[str] = mapped_column(Text)
    vendor: Mapped[str | None] = mapped_column(String(255))
    platform: Mapped[str | None] = mapped_column(String(255))

    # Read geometry stored as top-level fields
    read_type: Mapped[str] = mapped_column(String(50))
    read1_length: Mapped[int | None] = mapped_column(Integer)
    read2_length: Mapped[int | None] = mapped_column(Integer)
    index1_length: Mapped[int | None] = mapped_column(Integer)
    index2_length: Mapped[int | None] = mapped_column(Integer)

    # Lists stored as JSONB
    protocol_steps: Mapped[list] = mapped_column(JSONB, default=list)
    caveats: Mapped[list] = mapped_column(JSONB, default=list)
    source_urls: Mapped[list] = mapped_column(JSONB, default=list)

    library_structure: Mapped[list | None] = mapped_column(JSONB, default=None, nullable=True)

    confidence_score: Mapped[float] = mapped_column(Float)
    review_status: Mapped[str] = mapped_column(String(50), default="pending")
    extraction_notes: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime)
    schema_version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    version_number: Mapped[int] = mapped_column(Integer, default=1)

    # Relationships
    read_segments: Mapped[list["ReadSegmentRow"]] = relationship(
        back_populates="protocol", cascade="all, delete-orphan"
    )
    adapters: Mapped[list["AdapterRow"]] = relationship(
        back_populates="protocol", cascade="all, delete-orphan"
    )
    barcodes: Mapped[list["BarcodeSpecRow"]] = relationship(
        back_populates="protocol", cascade="all, delete-orphan"
    )
    reagent_kits: Mapped[list["ReagentKitRow"]] = relationship(
        back_populates="protocol", cascade="all, delete-orphan"
    )
    qc_expectations: Mapped[list["QCExpectationRow"]] = relationship(
        back_populates="protocol", cascade="all, delete-orphan"
    )
    failure_modes: Mapped[list["FailureModeRow"]] = relationship(
        back_populates="protocol", cascade="all, delete-orphan"
    )
    citations: Mapped[list["CitationRow"]] = relationship(
        secondary="protocol_citations", back_populates="protocols"
    )
    review_requests: Mapped[list["ReviewRequestRow"]] = relationship(
        back_populates="protocol"
    )
    versions: Mapped[list["ProtocolVersionRow"]] = relationship(
        back_populates="protocol", cascade="all, delete-orphan"
    )


class ReadSegmentRow(Base):
    __tablename__ = "read_segments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    protocol_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("protocols.id", ondelete="CASCADE")
    )
    role: Mapped[str] = mapped_column(String(50))
    read_number: Mapped[int] = mapped_column(Integer)
    start_pos: Mapped[int] = mapped_column(Integer)
    length: Mapped[int | None] = mapped_column(Integer)
    sequence: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)

    protocol: Mapped[ProtocolRow] = relationship(back_populates="read_segments")


class AdapterRow(Base):
    __tablename__ = "adapters"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    protocol_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("protocols.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(255))
    sequence: Mapped[str] = mapped_column(String(500))
    position: Mapped[str] = mapped_column(String(50))

    protocol: Mapped[ProtocolRow] = relationship(back_populates="adapters")


class BarcodeSpecRow(Base):
    __tablename__ = "barcode_specs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    protocol_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("protocols.id", ondelete="CASCADE")
    )
    role: Mapped[str] = mapped_column(String(50))
    length: Mapped[int] = mapped_column(Integer)
    whitelist_source: Mapped[str | None] = mapped_column(String(500))
    addition_method: Mapped[str | None] = mapped_column(String(100))

    protocol: Mapped[ProtocolRow] = relationship(back_populates="barcodes")


class ReagentKitRow(Base):
    __tablename__ = "reagent_kits"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    protocol_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("protocols.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(255))
    vendor: Mapped[str] = mapped_column(String(255))
    catalog_number: Mapped[str | None] = mapped_column(String(100))
    version: Mapped[str | None] = mapped_column(String(50))

    protocol: Mapped[ProtocolRow] = relationship(back_populates="reagent_kits")


class CitationRow(Base):
    __tablename__ = "citations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    doi: Mapped[str | None] = mapped_column(String(255))
    pmid: Mapped[str | None] = mapped_column(String(50))
    arxiv_id: Mapped[str | None] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(Text)
    authors: Mapped[list] = mapped_column(JSONB, default=list)
    year: Mapped[int | None] = mapped_column(Integer)
    url: Mapped[str | None] = mapped_column(String(500))

    protocols: Mapped[list[ProtocolRow]] = relationship(
        secondary="protocol_citations", back_populates="citations"
    )


class ProtocolCitationRow(Base):
    __tablename__ = "protocol_citations"

    protocol_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("protocols.id", ondelete="CASCADE"), primary_key=True
    )
    citation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("citations.id", ondelete="CASCADE"), primary_key=True
    )


class QCExpectationRow(Base):
    __tablename__ = "qc_expectations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    protocol_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("protocols.id", ondelete="CASCADE")
    )
    metric: Mapped[str] = mapped_column(String(255))
    typical_range_low: Mapped[float | None] = mapped_column(Float)
    typical_range_high: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text)

    protocol: Mapped[ProtocolRow] = relationship(back_populates="qc_expectations")


class FailureModeRow(Base):
    __tablename__ = "failure_modes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    protocol_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("protocols.id", ondelete="CASCADE")
    )
    description: Mapped[str] = mapped_column(Text)
    symptom: Mapped[str] = mapped_column(Text)
    likely_cause: Mapped[str] = mapped_column(Text)
    mitigation: Mapped[str | None] = mapped_column(Text)

    protocol: Mapped[ProtocolRow] = relationship(back_populates="failure_modes")


class SourceDocumentRow(Base):
    __tablename__ = "source_documents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    url: Mapped[str] = mapped_column(String(2000))
    title: Mapped[str | None] = mapped_column(String(500))
    source_type: Mapped[str] = mapped_column(String(50))
    content_hash: Mapped[str | None] = mapped_column(String(64))
    raw_text: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    discovered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime)
    submissions: Mapped[list["ProtocolSubmissionRow"]] = relationship(
        back_populates="source_document"
    )


class ReviewRequestRow(Base):
    __tablename__ = "review_requests"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    protocol_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("protocols.id", ondelete="CASCADE")
    )
    confidence_score: Mapped[float] = mapped_column(Float)
    extraction_notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    assigned_to: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    protocol: Mapped[ProtocolRow] = relationship(back_populates="review_requests")
    decisions: Mapped[list["ReviewDecisionRow"]] = relationship(
        back_populates="review_request"
    )
    submissions: Mapped[list["ProtocolSubmissionRow"]] = relationship(
        back_populates="review_request"
    )


class ReviewDecisionRow(Base):
    __tablename__ = "review_decisions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    review_request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("review_requests.id", ondelete="CASCADE")
    )
    reviewer: Mapped[str] = mapped_column(String(255))
    decision: Mapped[str] = mapped_column(String(50))
    comments: Mapped[str | None] = mapped_column(Text)
    edits: Mapped[dict | None] = mapped_column(JSONB)
    decided_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    review_request: Mapped[ReviewRequestRow] = relationship(back_populates="decisions")


class ProtocolVersionRow(Base):
    __tablename__ = "protocol_versions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    protocol_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("protocols.id", ondelete="CASCADE")
    )
    version_number: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[dict] = mapped_column(JSONB)
    change_summary: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_by: Mapped[str] = mapped_column(String(255), default="system")

    protocol: Mapped[ProtocolRow] = relationship(back_populates="versions")


class ProtocolSubmissionRow(Base):
    __tablename__ = "protocol_submissions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    source_url: Mapped[str] = mapped_column(String(2000))
    notes: Mapped[str | None] = mapped_column(Text)
    submitted_by: Mapped[str] = mapped_column(String(255), default="system")
    status: Mapped[str] = mapped_column(String(50), default="queued")
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("source_documents.id", ondelete="SET NULL")
    )
    protocol_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("protocols.id", ondelete="SET NULL")
    )
    review_request_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("review_requests.id", ondelete="SET NULL")
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    source_document: Mapped[SourceDocumentRow | None] = relationship(
        back_populates="submissions"
    )
    protocol: Mapped[ProtocolRow | None] = relationship()
    review_request: Mapped[ReviewRequestRow | None] = relationship(
        back_populates="submissions"
    )
    runs: Mapped[list["IngestionRunRow"]] = relationship(
        back_populates="submission", cascade="all, delete-orphan"
    )


class IngestionRunRow(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    submission_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("protocol_submissions.id", ondelete="CASCADE")
    )
    status: Mapped[str] = mapped_column(String(50), default="queued")
    stage: Mapped[str] = mapped_column(String(100), default="queued")
    results: Mapped[dict] = mapped_column(JSONB, default=dict)
    errors: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)

    submission: Mapped[ProtocolSubmissionRow] = relationship(back_populates="runs")


class ProtocolSeqSpecRow(Base):
    __tablename__ = "protocol_seqspecs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    protocol_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("protocols.id", ondelete="CASCADE"), unique=True
    )
    submission_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("protocol_submissions.id", ondelete="SET NULL")
    )
    content_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    content_yaml: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PipelineRunRow(Base):
    __tablename__ = "pipeline_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    status: Mapped[str] = mapped_column(String(50))  # running, completed, failed
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    protocols_processed: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[list] = mapped_column(JSONB, default=list)
