from enum import StrEnum


class AssayFamily(StrEnum):
    SCRNA_SEQ = "scRNA-seq"
    SCATAC_SEQ = "scATAC-seq"
    SPATIAL_TRANSCRIPTOMICS = "spatial-transcriptomics"
    MULTIOME = "multiome"
    BULK_RNA_SEQ = "bulk-RNA-seq"
    SINGLE_CELL_DNA = "scDNA"
    METHYLATION = "methylation"
    CITE_SEQ = "CITE-seq"
    OTHER = "other"


class MoleculeType(StrEnum):
    RNA = "RNA"
    DNA = "DNA"
    PROTEIN = "protein"
    CHROMATIN = "chromatin"
    MULTI = "multi"


class ReadType(StrEnum):
    PAIRED_END = "paired-end"
    SINGLE_END = "single-end"


class SegmentRole(StrEnum):
    CELL_BARCODE = "cell_barcode"
    UMI = "umi"
    CDNA = "cdna"
    SAMPLE_INDEX = "sample_index"
    LINKER = "linker"
    SPACER = "spacer"
    PRIMER = "primer"
    ADAPTER = "adapter"
    FEATURE_BARCODE = "feature_barcode"
    GENOMIC_INSERT = "genomic_insert"
    OTHER = "other"


class ReviewStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"


class ConfidenceLevel(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class IngestionStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
