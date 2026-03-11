const DEFAULT_DEV_BASE_URL = 'http://127.0.0.1:8000';
export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ??
  (import.meta.env.DEV ? DEFAULT_DEV_BASE_URL : '')
).replace(/\/+$/, '');

function joinUrl(path: string): string {
  return `${API_BASE_URL}${path.startsWith('/') ? path : `/${path}`}`;
}

export function apiUrl(path: string): string {
  return joinUrl(path);
}

async function parseErrorBody(res: Response): Promise<string> {
  const text = await res.text().catch(() => res.statusText);
  const compact = text.trim();

  if (!compact) {
    return res.statusText;
  }

  if (compact.startsWith('<')) {
    if (compact.toLowerCase().includes('ngrok')) {
      return 'Received HTML from ngrok instead of JSON. Confirm the tunnel is active and that the request includes the ngrok skip-browser-warning header.';
    }
    return 'Received HTML instead of JSON from the API.';
  }

  return compact;
}

async function requestJson<T>(path: string, options?: RequestInit): Promise<T> {
  const headers = new Headers(options?.headers);
  headers.set('Accept', 'application/json');
  headers.set('ngrok-skip-browser-warning', 'true');

  const hasBody = options?.body !== undefined && options?.body !== null;
  const isFormData = typeof FormData !== 'undefined' && options?.body instanceof FormData;
  if (hasBody && !isFormData && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const res = await fetch(joinUrl(path), {
    ...options,
    headers,
  });

  if (!res.ok) {
    throw new Error(`${res.status}: ${await parseErrorBody(res)}`);
  }

  const contentType = res.headers.get('content-type') ?? '';
  if (!contentType.includes('application/json')) {
    const body = await res.text().catch(() => '');
    if (body.trim().startsWith('<')) {
      throw new Error(
        'Expected JSON but received HTML. This usually means the request hit an ngrok browser warning page or an HTML route like /reviews.',
      );
    }
    throw new Error(`Expected JSON but received ${contentType || 'an unknown content type'}.`);
  }

  return res.json() as Promise<T>;
}

export type ReviewStatus = 'pending' | 'approved' | 'rejected' | 'needs_revision';
export type SubmissionStatus = 'queued' | 'running' | 'completed' | 'failed';
export type SegmentRole =
  | 'cell_barcode'
  | 'umi'
  | 'cdna'
  | 'sample_index'
  | 'linker'
  | 'spacer'
  | 'primer'
  | 'adapter'
  | 'feature_barcode'
  | 'genomic_insert'
  | 'other';

export interface ProtocolListItem {
  id?: string;
  slug: string;
  name: string;
  version?: string;
  assay_family?: string | null;
  molecule_type?: string | null;
  vendor?: string | null;
  description?: string | null;
  confidence_score?: number | null;
  review_status?: ReviewStatus | null;
}

export interface ReadSegment {
  role: SegmentRole;
  read_number: number;
  start_pos: number;
  length?: number | null;
  sequence?: string | null;
  description?: string | null;
}

export interface ReadGeometry {
  read_type?: string | null;
  read1_length?: number | null;
  read2_length?: number | null;
  index1_length?: number | null;
  index2_length?: number | null;
  segments: ReadSegment[];
}

export interface Adapter {
  name: string;
  sequence: string;
  position: string;
}

export interface Barcode {
  role: SegmentRole;
  length: number;
  whitelist_source?: string | null;
  addition_method?: string | null;
}

export interface Citation {
  doi?: string | null;
  pmid?: string | null;
  arxiv_id?: string | null;
  title: string;
  authors: string[];
  year?: number | null;
  url?: string | null;
}

export interface ReagentKit {
  name: string;
  vendor: string;
  catalog_number?: string | null;
  version?: string | null;
}

export interface QCExpectation {
  metric: string;
  typical_range_low?: number | null;
  typical_range_high?: number | null;
  notes?: string | null;
}

export interface FailureMode {
  description: string;
  symptom: string;
  likely_cause: string;
  mitigation?: string | null;
}

export interface LibraryRegion {
  type: string;
  top: string;
  bottom: string;
  label?: string | null;
}

export interface FieldEvidence {
  field_path: string;
  label: string;
  value?: string | null;
  segment_id?: string | null;
  source_url?: string | null;
  excerpt?: string | null;
  page_reference?: string | null;
  extraction_mode: 'extracted' | 'inferred' | string;
  confidence_score?: number | null;
  review_status?: ReviewStatus | null;
  parser_stage?: string | null;
  parser_source?: string | null;
  notes?: string | null;
}

export interface ProtocolTimelineStep {
  step_id: string;
  title: string;
  summary?: string | null;
  introduced_segment_ids: string[];
  modified_segment_ids: string[];
  highlighted_field_paths: string[];
}

export interface ExplorerSegmentReadMapping {
  read_key: string;
  label: string;
  start_cycle: number;
  end_cycle: number;
}

export interface ExplorerSegment {
  segment_id: string;
  label: string;
  kind: string;
  role?: SegmentRole | null;
  sequence?: string | null;
  length?: number | null;
  description?: string | null;
  introduced_by_step_id?: string | null;
  modified_by_step_ids: string[];
  preprocessing_group?: string | null;
  read_mappings: ExplorerSegmentReadMapping[];
}

export interface ExplorerReadTrace {
  read_key: string;
  label: string;
  length?: number | null;
  segments: string[];
}

export interface ExplorerPreprocessingGroup {
  group_id: string;
  label: string;
  description?: string | null;
  segment_ids: string[];
}

export interface ProtocolExplorerHeader {
  assay_name: string;
  chemistry_version?: string | null;
  assay_family?: string | null;
  vendor?: string | null;
  compatible_instruments: string[];
  confidence_score: number;
  review_status?: ReviewStatus | null;
  source_links: string[];
  last_updated?: string | null;
  revision?: string | null;
}

export interface SequencingRecipe {
  read1_length?: number | null;
  read2_length?: number | null;
  index1_length?: number | null;
  index2_length?: number | null;
  custom_primer_required?: boolean | null;
  supported_instruments: string[];
  orientation_notes?: string | null;
  read_structure_string?: string | null;
}

export interface ExportArtifact {
  export_id: string;
  label: string;
  format: string;
  href?: string | null;
  copy_text?: string | null;
}

export interface ProtocolExplorer {
  header: ProtocolExplorerHeader;
  blueprint_segments: ExplorerSegment[];
  sequencer_reads: ExplorerReadTrace[];
  preprocessing_groups: ExplorerPreprocessingGroup[];
  timeline: ProtocolTimelineStep[];
  recipe: SequencingRecipe;
  evidence: FieldEvidence[];
  exports: ExportArtifact[];
  citations: Citation[];
  description?: string | null;
  extraction_notes?: string | null;
}

export interface ProtocolDetail extends ProtocolListItem {
  platform?: string | null;
  chemistry_version?: string | null;
  compatible_instruments: string[];
  custom_primer_required?: boolean | null;
  strand_orientation_notes?: string | null;
  read_geometry: ReadGeometry;
  adapters: Adapter[];
  barcodes: Barcode[];
  reagent_kits: ReagentKit[];
  protocol_steps: string[];
  protocol_timeline: ProtocolTimelineStep[];
  qc_expectations: QCExpectation[];
  failure_modes: FailureMode[];
  caveats: string[];
  citations: Citation[];
  source_urls: string[];
  library_structure?: LibraryRegion[] | null;
  field_evidence: FieldEvidence[];
  parser_config?: Record<string, unknown> | null;
  extraction_notes?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  published_at?: string | null;
  schema_version?: string | null;
}

export interface IngestionRun {
  id: string;
  status: SubmissionStatus;
  stage?: string | null;
  results?: Record<string, unknown> | null;
  errors?: string[] | null;
  created_at?: string | null;
  completed_at?: string | null;
}

export interface Submission {
  id: string;
  source_url: string;
  notes?: string | null;
  submitted_by?: string | null;
  status: SubmissionStatus;
  source_document_id?: string | null;
  protocol_id?: string | null;
  protocol_slug?: string | null;
  review_request_id?: string | null;
  error_message?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  latest_run?: IngestionRun | null;
}

export interface ReviewListItem {
  id: string;
  protocol_id: string;
  protocol_slug?: string | null;
  protocol_name?: string | null;
  confidence_score: number;
  status: ReviewStatus;
  created_at?: string | null;
  extraction_notes?: string | null;
  submission_id?: string | null;
  source_url?: string | null;
  duplicate_submission: boolean;
}

export interface ReviewDiff {
  field: string;
  current?: unknown;
  draft?: unknown;
  current_text?: string | null;
  draft_text?: string | null;
}

export interface ReviewComparison {
  review: {
    id: string;
    status: ReviewStatus;
    confidence_score: number;
    created_at?: string | null;
    extraction_notes?: string | null;
    duplicate_submission: boolean;
    submission_id?: string | null;
    source_url?: string | null;
  };
  current_protocol: ProtocolDetail;
  draft_protocol: ProtocolDetail;
  diffs: ReviewDiff[];
}

export const api = {
  health: () => requestJson<Record<string, unknown>>('/health'),
  protocols: {
    list: (params?: { assay_family?: string; limit?: number; offset?: number }) => {
      const qs = new URLSearchParams();
      if (params?.assay_family) qs.set('assay_family', params.assay_family);
      if (params?.limit != null) qs.set('limit', String(params.limit));
      if (params?.offset != null) qs.set('offset', String(params.offset));
      const query = qs.toString();
      return requestJson<ProtocolListItem[]>(query ? `/protocols?${query}` : '/protocols');
    },
    get: (slug: string) => requestJson<ProtocolDetail>(`/protocols/${slug}`),
    explorer: (slug: string) => requestJson<ProtocolExplorer>(`/protocols/${slug}/explorer`),
    readGeometry: (slug: string) =>
      requestJson<ReadGeometry>(`/protocols/${slug}/read-geometry`),
    seqspec: (slug: string) => requestJson<unknown>(`/protocols/${slug}/seqspec`),
  },
  submissions: {
    list: (params?: { limit?: number; offset?: number }) => {
      const qs = new URLSearchParams();
      if (params?.limit != null) qs.set('limit', String(params.limit));
      if (params?.offset != null) qs.set('offset', String(params.offset));
      const query = qs.toString();
      return requestJson<Submission[]>(query ? `/submissions?${query}` : '/submissions');
    },
    get: (id: string) => requestJson<Submission>(`/submissions/${id}`),
  },
  reviews: {
    list: () => requestJson<ReviewListItem[]>('/reviews/api'),
    comparison: (id: string) => requestJson<ReviewComparison>(`/reviews/${id}/comparison`),
    decide: (id: string, payload: { decision: ReviewStatus; comments?: string }) =>
      requestJson<{ id: string; status: ReviewStatus }>(`/reviews/${id}/decision`, {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
  },
};
