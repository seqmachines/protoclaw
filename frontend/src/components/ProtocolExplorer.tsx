import { useMemo, useState } from 'react';
import {
  ArrowUpRight,
  Copy,
  ExternalLink,
  FlaskConical,
  Layers3,
  Microscope,
  ScanLine,
  ScrollText,
  TimerReset,
} from 'lucide-react';

import { ReviewStatusBadge, ConfidenceScore } from '@/components/StatusBadge';
import { Button } from '@/components/ui/button';
import { Drawer, DrawerContent, DrawerDescription, DrawerHeader, DrawerTitle } from '@/components/ui/drawer';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { useIsMobile } from '@/hooks/use-mobile';
import { useToast } from '@/hooks/use-toast';
import {
  apiUrl,
  type ExplorerSegment,
  type FieldEvidence,
  type ProtocolExplorer,
  type ProtocolTimelineStep,
} from '@/lib/api';
import { cn } from '@/lib/utils';

type ViewMode = 'molecule' | 'sequencer' | 'preprocessing';

const SEGMENT_COLORS: Record<string, { fill: string; stroke: string; accent: string }> = {
  p5: { fill: '#d8ebff', stroke: '#2261a8', accent: '#2261a8' },
  p7: { fill: '#ffe0db', stroke: '#b6432a', accent: '#b6432a' },
  r1_primer: { fill: '#e7f7ef', stroke: '#27795d', accent: '#27795d' },
  cbc: { fill: '#ffe3ef', stroke: '#bc2d72', accent: '#bc2d72' },
  cell_barcode: { fill: '#ffe3ef', stroke: '#bc2d72', accent: '#bc2d72' },
  umi: { fill: '#ece5ff', stroke: '#5b38a5', accent: '#5b38a5' },
  poly_dt: { fill: '#ecf8df', stroke: '#557d15', accent: '#557d15' },
  cdna: { fill: '#f2f0eb', stroke: '#625a49', accent: '#625a49' },
  insert: { fill: '#f2f0eb', stroke: '#625a49', accent: '#625a49' },
  i7: { fill: '#fff0d9', stroke: '#b56812', accent: '#b56812' },
  i5: { fill: '#fff4df', stroke: '#8d6200', accent: '#8d6200' },
  index: { fill: '#fff0d9', stroke: '#b56812', accent: '#b56812' },
  adapter: { fill: '#e7ecf4', stroke: '#50627a', accent: '#50627a' },
  sample_index: { fill: '#fff0d9', stroke: '#b56812', accent: '#b56812' },
};

const DEFAULT_SEGMENT_COLOR = { fill: '#edf1f4', stroke: '#5d6976', accent: '#5d6976' };

function segmentColor(segment: ExplorerSegment) {
  return SEGMENT_COLORS[segment.kind] ?? SEGMENT_COLORS[segment.role ?? ''] ?? DEFAULT_SEGMENT_COLOR;
}

function segmentWidth(segment: ExplorerSegment) {
  const base = 110;
  const length = segment.length ?? 10;
  return Math.max(base, Math.min(220, 64 + length * 4));
}

function formatDate(value?: string | null) {
  if (!value) return 'Unknown';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
}

function isSegmentHighlighted(segment: ExplorerSegment, highlightedSegmentIds: Set<string>, selectedStep?: ProtocolTimelineStep | null) {
  if (highlightedSegmentIds.has(segment.segment_id)) {
    return true;
  }
  if (!selectedStep) {
    return false;
  }
  return (
    selectedStep.introduced_segment_ids.includes(segment.segment_id) ||
    selectedStep.modified_segment_ids.includes(segment.segment_id)
  );
}

function EvidencePanel({
  evidence,
  title,
}: {
  evidence: FieldEvidence[];
  title: string;
}) {
  return (
    <div className="space-y-3">
      <div className="border-b border-border/70 pb-3">
        <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">Evidence drawer</p>
        <h3 className="mt-1 text-lg font-semibold">{title}</h3>
      </div>

      {evidence.length === 0 && (
        <div className="rounded-[1.25rem] border border-dashed border-border bg-white/70 p-4 text-sm text-muted-foreground">
          No field-level provenance is available for the current selection.
        </div>
      )}

      {evidence.map((item) => (
        <article key={`${item.field_path}-${item.label}-${item.segment_id ?? 'field'}`} className="rounded-[1.25rem] border border-border bg-white p-4 shadow-[0_12px_30px_rgba(16,24,40,0.06)]">
          <div className="flex flex-wrap items-center gap-2">
            <span className="stat-pill">{item.label}</span>
            <span className={cn('status-badge', item.extraction_mode === 'extracted' ? 'border-emerald-300 bg-emerald-50 text-emerald-700' : 'border-amber-300 bg-amber-50 text-amber-700')}>
              {item.extraction_mode}
            </span>
            {item.review_status && <ReviewStatusBadge status={item.review_status} />}
            {item.confidence_score != null && <ConfidenceScore score={item.confidence_score} />}
          </div>

          {item.value && <p className="mt-3 text-sm font-medium text-foreground">{item.value}</p>}
          {item.excerpt && <p className="mt-3 text-sm leading-6 text-muted-foreground">"{item.excerpt}"</p>}

          <dl className="mt-4 grid gap-3 text-xs text-muted-foreground">
            <div>
              <dt className="data-label">Field path</dt>
              <dd className="mt-1 font-mono">{item.field_path}</dd>
            </div>
            {item.page_reference && (
              <div>
                <dt className="data-label">Page / section</dt>
                <dd className="mt-1">{item.page_reference}</dd>
              </div>
            )}
            {(item.parser_stage || item.parser_source) && (
              <div>
                <dt className="data-label">Parser metadata</dt>
                <dd className="mt-1">
                  {[item.parser_stage, item.parser_source].filter(Boolean).join(' · ')}
                </dd>
              </div>
            )}
            {item.notes && (
              <div>
                <dt className="data-label">Notes</dt>
                <dd className="mt-1">{item.notes}</dd>
              </div>
            )}
          </dl>

          {item.source_url && (
            <a
              href={item.source_url}
              target="_blank"
              rel="noreferrer"
              className="mt-4 inline-flex items-center gap-2 text-xs uppercase tracking-[0.18em] text-muted-foreground hover:text-foreground"
            >
              Source link
              <ExternalLink className="h-3.5 w-3.5" />
            </a>
          )}
        </article>
      ))}
    </div>
  );
}

function SegmentTooltip({ segment }: { segment: ExplorerSegment }) {
  return (
    <div className="max-w-[16rem] space-y-2 text-left">
      <div className="flex items-center justify-between gap-3">
        <p className="font-semibold">{segment.label}</p>
        {segment.length != null && <span className="font-mono text-xs text-muted-foreground">{segment.length} nt</span>}
      </div>
      <p className="text-xs text-muted-foreground">{segment.description ?? segment.kind}</p>
      {segment.sequence && <p className="font-mono text-[11px] text-foreground">{segment.sequence}</p>}
      {segment.read_mappings.length > 0 && (
        <p className="text-[11px] text-muted-foreground">
          {segment.read_mappings.map((mapping) => mapping.read_key).join(', ')}
        </p>
      )}
    </div>
  );
}

function Blueprint({
  explorer,
  activeView,
  highlightedSegmentIds,
  selectedStep,
  onSelectSegment,
  onActiveViewChange,
}: {
  explorer: ProtocolExplorer;
  activeView: ViewMode;
  highlightedSegmentIds: Set<string>;
  selectedStep?: ProtocolTimelineStep | null;
  onSelectSegment: (segmentId: string) => void;
  onActiveViewChange: (view: ViewMode) => void;
}) {
  return (
    <section className="explorer-panel overflow-hidden">
      <div className="explorer-panel-header">
        <div>
          <p className="explorer-kicker">Interactive library blueprint</p>
          <h2 className="text-xl font-semibold">Molecule to reads</h2>
        </div>
        <Tabs value={activeView} onValueChange={(value) => onActiveViewChange(value as ViewMode)} className="w-full max-w-[24rem]">
          <TabsList className="grid w-full grid-cols-3 rounded-full bg-[#f3efe7] p-1">
            <TabsTrigger value="molecule" className="rounded-full text-xs uppercase tracking-[0.16em]">Molecule</TabsTrigger>
            <TabsTrigger value="sequencer" className="rounded-full text-xs uppercase tracking-[0.16em]">Sequencer</TabsTrigger>
            <TabsTrigger value="preprocessing" className="rounded-full text-xs uppercase tracking-[0.16em]">Preprocess</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      <div className="relative overflow-x-auto pb-2">
        <div className="mb-4 flex items-center justify-between text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
          <span>5' construct</span>
          <span>3' construct</span>
        </div>

        <div className="flex min-w-max gap-3">
          {explorer.blueprint_segments.map((segment, index) => {
            const width = segmentWidth(segment);
            const color = segmentColor(segment);
            const highlighted = isSegmentHighlighted(segment, highlightedSegmentIds, selectedStep);
            const activeRead = activeView === 'sequencer' ? segment.read_mappings[0]?.read_key : null;
            const preprocessLabel = activeView === 'preprocessing' ? segment.preprocessing_group?.replace('_', ' ') : null;

            return (
              <Tooltip key={segment.segment_id}>
                <TooltipTrigger asChild>
                  <button
                    type="button"
                    className={cn('explorer-segment', highlighted && 'explorer-segment-active')}
                    style={{ width, animationDelay: `${index * 90}ms` }}
                    onClick={() => onSelectSegment(segment.segment_id)}
                  >
                    <svg viewBox={`0 0 ${width} 138`} width={width} height={138} className="overflow-visible">
                      <rect
                        x="1.5"
                        y="24"
                        width={width - 3}
                        height="70"
                        rx="18"
                        fill={color.fill}
                        stroke={color.stroke}
                        strokeWidth={highlighted ? 3 : 1.5}
                      />
                      <text x={width / 2} y="52" textAnchor="middle" fontSize="12" fontWeight="700" fill={color.stroke}>
                        {segment.label}
                      </text>
                      <text x={width / 2} y="71" textAnchor="middle" fontSize="10" fill={color.stroke}>
                        {segment.length != null ? `${segment.length} nt` : 'variable'}
                      </text>
                      <text x={width / 2} y="89" textAnchor="middle" fontSize="10" fill={color.stroke} opacity="0.88">
                        {activeView === 'molecule'
                          ? segment.kind.replaceAll('_', ' ')
                          : activeView === 'sequencer'
                            ? activeRead ?? 'unread'
                            : preprocessLabel ?? 'library'}
                      </text>

                      {activeView === 'sequencer' && segment.read_mappings.length > 0 && (
                        <g className="cycle-sweep">
                          <rect
                            x="12"
                            y="104"
                            width={width - 24}
                            height="12"
                            rx="6"
                            fill={color.accent}
                            opacity="0.16"
                          />
                          <rect
                            x="12"
                            y="104"
                            width={Math.max(28, width * 0.38)}
                            height="12"
                            rx="6"
                            fill={color.accent}
                            opacity="0.9"
                          />
                        </g>
                      )}

                      {activeView === 'preprocessing' && preprocessLabel && (
                        <rect x="16" y="8" width={width - 32} height="12" rx="6" fill={color.accent} opacity="0.16" />
                      )}
                    </svg>
                  </button>
                </TooltipTrigger>
                <TooltipContent side="top" className="max-w-sm rounded-2xl border border-border bg-white p-3 shadow-xl">
                  <SegmentTooltip segment={segment} />
                </TooltipContent>
              </Tooltip>
            );
          })}
        </div>
      </div>

      {activeView === 'sequencer' && (
        <div className="mt-6 grid gap-3 lg:grid-cols-2">
          {explorer.sequencer_reads.map((read) => (
            <div key={read.read_key} className="rounded-[1.25rem] border border-border bg-white/80 p-4">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground">{read.read_key}</p>
                  <p className="font-semibold">{read.label}</p>
                </div>
                <span className="stat-pill">{read.length != null ? `${read.length} cycles` : 'variable'}</span>
              </div>
              <ul className="mt-4 space-y-2 text-sm text-muted-foreground">
                {read.segments.map((segment) => (
                  <li key={segment} className="rounded-xl bg-[#f7f3eb] px-3 py-2">{segment}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}

      {activeView === 'preprocessing' && (
        <div className="mt-6 grid gap-3 lg:grid-cols-3">
          {explorer.preprocessing_groups.map((group) => (
            <div key={group.group_id} className="rounded-[1.25rem] border border-border bg-white/80 p-4">
              <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground">{group.group_id}</p>
              <h3 className="mt-2 font-semibold">{group.label}</h3>
              {group.description && <p className="mt-2 text-sm text-muted-foreground">{group.description}</p>}
              <div className="mt-4 flex flex-wrap gap-2">
                {group.segment_ids.map((segmentId) => {
                  const segment = explorer.blueprint_segments.find((item) => item.segment_id === segmentId);
                  return (
                    <button
                      key={segmentId}
                      type="button"
                      className="stat-pill"
                      onClick={() => onSelectSegment(segmentId)}
                    >
                      {segment?.label ?? segmentId}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function Timeline({
  timeline,
  selectedStepId,
  onSelectStep,
}: {
  timeline: ProtocolTimelineStep[];
  selectedStepId?: string | null;
  onSelectStep: (stepId: string | null) => void;
}) {
  return (
    <section className="explorer-panel">
      <div className="explorer-panel-header">
        <div>
          <p className="explorer-kicker">Protocol generation</p>
          <h2 className="text-xl font-semibold">Step-by-step timeline</h2>
        </div>
        <Button variant="ghost" className="rounded-full text-xs uppercase tracking-[0.16em]" onClick={() => onSelectStep(null)}>
          Clear focus
        </Button>
      </div>
      <div className="space-y-3">
        {timeline.map((step, index) => {
          const selected = selectedStepId === step.step_id;
          return (
            <button
              key={step.step_id}
              type="button"
              onClick={() => onSelectStep(selected ? null : step.step_id)}
              className={cn(
                'timeline-step',
                selected && 'timeline-step-active',
              )}
            >
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full border border-current font-mono text-xs">
                {String(index + 1).padStart(2, '0')}
              </div>
              <div className="min-w-0 flex-1 text-left">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="font-semibold">{step.title}</h3>
                  {step.introduced_segment_ids.length > 0 && <span className="stat-pill">{step.introduced_segment_ids.length} introduced</span>}
                  {step.modified_segment_ids.length > 0 && <span className="stat-pill">{step.modified_segment_ids.length} modified</span>}
                </div>
                {step.summary && <p className="mt-2 text-sm text-muted-foreground">{step.summary}</p>}
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );
}

function RecipePanel({ explorer }: { explorer: ProtocolExplorer }) {
  const recipeCards = [
    { label: 'Read 1', value: explorer.recipe.read1_length != null ? `${explorer.recipe.read1_length} cycles` : 'n/a', icon: ScanLine },
    { label: 'Read 2', value: explorer.recipe.read2_length != null ? `${explorer.recipe.read2_length} cycles` : 'n/a', icon: ScanLine },
    { label: 'Index 1', value: explorer.recipe.index1_length != null ? `${explorer.recipe.index1_length} cycles` : 'n/a', icon: Layers3 },
    { label: 'Index 2', value: explorer.recipe.index2_length != null ? `${explorer.recipe.index2_length} cycles` : 'n/a', icon: Layers3 },
  ];

  return (
    <section className="explorer-panel">
      <div className="explorer-panel-header">
        <div>
          <p className="explorer-kicker">Sequencing recipe</p>
          <h2 className="text-xl font-semibold">Run configuration</h2>
        </div>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        {recipeCards.map(({ label, value, icon: Icon }) => (
          <div key={label} className="rounded-[1.25rem] border border-border bg-white/80 p-4">
            <div className="flex items-center gap-3">
              <span className="flex h-10 w-10 items-center justify-center rounded-full bg-[#eef1f4] text-[#3d4b5d]">
                <Icon className="h-4 w-4" />
              </span>
              <div>
                <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground">{label}</p>
                <p className="font-semibold">{value}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
      <div className="mt-4 grid gap-3 xl:grid-cols-3">
        <div className="rounded-[1.25rem] border border-border bg-white/80 p-4">
          <p className="data-label">Custom primer</p>
          <p className="mt-2 text-sm font-medium">{explorer.recipe.custom_primer_required == null ? 'Unknown' : explorer.recipe.custom_primer_required ? 'Required' : 'Not required'}</p>
        </div>
        <div className="rounded-[1.25rem] border border-border bg-white/80 p-4 xl:col-span-2">
          <p className="data-label">Supported instruments</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {explorer.recipe.supported_instruments.length > 0 ? explorer.recipe.supported_instruments.map((instrument) => (
              <span key={instrument} className="stat-pill">{instrument}</span>
            )) : <span className="text-sm text-muted-foreground">No instrument guidance stored.</span>}
          </div>
        </div>
      </div>
      {explorer.recipe.orientation_notes && (
        <div className="mt-4 rounded-[1.25rem] border border-border bg-white/80 p-4">
          <p className="data-label">Orientation notes</p>
          <p className="mt-2 text-sm text-muted-foreground">{explorer.recipe.orientation_notes}</p>
        </div>
      )}
      {explorer.recipe.read_structure_string && (
        <div className="mt-4 rounded-[1.25rem] border border-border bg-[#171c23] p-4 text-[#f4efe6]">
          <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#c8d0dc]">Read structure</p>
          <p className="mt-3 font-mono text-sm">{explorer.recipe.read_structure_string}</p>
        </div>
      )}
    </section>
  );
}

function ExportPanel({ explorer }: { explorer: ProtocolExplorer }) {
  const { toast } = useToast();

  async function handleExportCopy(text: string) {
    await navigator.clipboard.writeText(text);
    toast({ title: 'Copied', description: 'Read structure copied to clipboard.' });
  }

  return (
    <section className="explorer-panel">
      <div className="explorer-panel-header">
        <div>
          <p className="explorer-kicker">Export panel</p>
          <h2 className="text-xl font-semibold">Artifacts</h2>
        </div>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        {explorer.exports.map((item) => (
          <div key={item.export_id} className="rounded-[1.25rem] border border-border bg-white/80 p-4">
            <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground">{item.format}</p>
            <h3 className="mt-2 font-semibold">{item.label}</h3>
              <div className="mt-4 flex flex-wrap gap-2">
              {item.href && (
                <Button asChild className="rounded-full bg-[#1a242e] px-4 text-xs uppercase tracking-[0.16em] text-white hover:bg-[#24313d]">
                  <a href={apiUrl(item.href)} target="_blank" rel="noreferrer">
                    Open
                    <ArrowUpRight className="ml-2 h-3.5 w-3.5" />
                  </a>
                </Button>
              )}
              {item.copy_text && (
                <Button
                  variant="outline"
                  className="rounded-full text-xs uppercase tracking-[0.16em]"
                  onClick={() => handleExportCopy(item.copy_text!)}
                >
                  <Copy className="mr-2 h-3.5 w-3.5" />
                  Copy
                </Button>
              )}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

export function ProtocolExplorerView({ slug, explorer }: { slug: string; explorer: ProtocolExplorer }) {
  const isMobile = useIsMobile();
  const [activeView, setActiveView] = useState<ViewMode>('molecule');
  const [selectedSegmentId, setSelectedSegmentId] = useState<string | null>(explorer.blueprint_segments[0]?.segment_id ?? null);
  const [selectedFieldPath, setSelectedFieldPath] = useState<string | null>('name');
  const [selectedStepId, setSelectedStepId] = useState<string | null>(explorer.timeline[0]?.step_id ?? null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const selectedStep = explorer.timeline.find((step) => step.step_id === selectedStepId) ?? null;
  const highlightedSegmentIds = useMemo(() => {
    const ids = new Set<string>();
    if (selectedSegmentId) ids.add(selectedSegmentId);
    if (selectedStep) {
      selectedStep.introduced_segment_ids.forEach((id) => ids.add(id));
      selectedStep.modified_segment_ids.forEach((id) => ids.add(id));
    }
    return ids;
  }, [selectedSegmentId, selectedStep]);

  const evidenceTitle = selectedSegmentId
    ? explorer.blueprint_segments.find((segment) => segment.segment_id === selectedSegmentId)?.label ?? 'Selection'
    : selectedFieldPath ?? 'Selection';

  const activeEvidence = useMemo(() => {
    const bySegment = selectedSegmentId
      ? explorer.evidence.filter((item) => item.segment_id === selectedSegmentId)
      : [];
    if (bySegment.length > 0) {
      return bySegment;
    }
    const byField = selectedFieldPath
      ? explorer.evidence.filter((item) => item.field_path === selectedFieldPath)
      : [];
    if (byField.length > 0) {
      return byField;
    }
    if (selectedStep) {
      return explorer.evidence.filter(
        (item) =>
          (item.segment_id && (
            selectedStep.introduced_segment_ids.includes(item.segment_id) ||
            selectedStep.modified_segment_ids.includes(item.segment_id)
          )) ||
          selectedStep.highlighted_field_paths.includes(item.field_path),
      );
    }
    return [];
  }, [explorer.evidence, selectedFieldPath, selectedSegmentId, selectedStep]);

  function handleSelectSegment(segmentId: string) {
    setSelectedSegmentId(segmentId);
    setSelectedFieldPath(null);
    if (isMobile) {
      setDrawerOpen(true);
    }
  }

  function handleFieldFocus(fieldPath: string) {
    setSelectedFieldPath(fieldPath);
    setSelectedSegmentId(null);
    if (isMobile) {
      setDrawerOpen(true);
    }
  }

  function handleStep(stepId: string | null) {
    setSelectedStepId(stepId);
    if (!stepId) {
      return;
    }
    const step = explorer.timeline.find((item) => item.step_id === stepId);
    const nextSegmentId = step?.introduced_segment_ids[0] ?? step?.modified_segment_ids[0] ?? null;
    if (nextSegmentId) {
      setSelectedSegmentId(nextSegmentId);
      setSelectedFieldPath(null);
    }
  }

  return (
    <div className="space-y-6">
      <section className="explorer-hero">
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1.5fr)_360px]">
          <div>
            <p className="explorer-kicker">Protocol explorer</p>
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <h1 className="text-4xl font-semibold tracking-[-0.03em] text-[#12202f]">{explorer.header.assay_name}</h1>
              <button type="button" className="stat-pill" onClick={() => handleFieldFocus('chemistry_version')}>
                {explorer.header.chemistry_version ?? 'Version unknown'}
              </button>
              <ReviewStatusBadge status={explorer.header.review_status} />
              <ConfidenceScore score={explorer.header.confidence_score} />
            </div>
            <p className="mt-4 max-w-3xl text-base text-[#435160]">{explorer.description}</p>
            {explorer.extraction_notes && (
              <div className="mt-4 rounded-[1.25rem] border border-white/60 bg-white/70 p-4 text-sm text-muted-foreground">
                {explorer.extraction_notes}
              </div>
            )}
            <div className="mt-6 flex flex-wrap gap-3">
              <button type="button" className="explorer-fact" onClick={() => handleFieldFocus('assay_family')}>
                <Microscope className="h-4 w-4" />
                <span>{explorer.header.assay_family}</span>
              </button>
              {explorer.header.vendor && (
                <button type="button" className="explorer-fact" onClick={() => handleFieldFocus('vendor')}>
                  <FlaskConical className="h-4 w-4" />
                  <span>{explorer.header.vendor}</span>
                </button>
              )}
              <button type="button" className="explorer-fact" onClick={() => handleFieldFocus('updated_at')}>
                <TimerReset className="h-4 w-4" />
                <span>Updated {formatDate(explorer.header.last_updated)}</span>
              </button>
              {explorer.header.revision && (
                <button type="button" className="explorer-fact" onClick={() => handleFieldFocus('schema_version')}>
                  <ScrollText className="h-4 w-4" />
                  <span>Revision {explorer.header.revision}</span>
                </button>
              )}
            </div>
          </div>

          <aside className="rounded-[1.75rem] border border-white/70 bg-white/80 p-5 shadow-[0_18px_50px_rgba(16,24,40,0.10)]">
            <p className="explorer-kicker">Compatible instruments</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {explorer.header.compatible_instruments.length > 0 ? explorer.header.compatible_instruments.map((instrument) => (
                <span key={instrument} className="stat-pill">{instrument}</span>
              )) : <span className="text-sm text-muted-foreground">No instrument guidance</span>}
            </div>

            <p className="mt-6 explorer-kicker">Sources</p>
            <div className="mt-3 space-y-2">
              {explorer.header.source_links.map((link) => (
                <a
                  key={link}
                  href={link}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center justify-between gap-3 rounded-xl border border-border bg-[#fbfaf6] px-3 py-3 text-sm text-muted-foreground hover:text-foreground"
                >
                  <span className="break-all">{link}</span>
                  <ExternalLink className="h-4 w-4 shrink-0" />
                </a>
              ))}
            </div>
          </aside>
        </div>
      </section>

      <Blueprint
        explorer={explorer}
        activeView={activeView}
        highlightedSegmentIds={highlightedSegmentIds}
        selectedStep={selectedStep}
        onSelectSegment={handleSelectSegment}
        onActiveViewChange={setActiveView}
      />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_360px]">
        <div className="space-y-6">
          <Timeline timeline={explorer.timeline} selectedStepId={selectedStepId} onSelectStep={handleStep} />
          <RecipePanel explorer={explorer} />
          <ExportPanel explorer={explorer} />
        </div>

        {!isMobile && (
          <aside className="space-y-6">
            <EvidencePanel evidence={activeEvidence} title={evidenceTitle} />
            {explorer.citations.length > 0 && (
              <section className="explorer-panel">
                <div className="explorer-panel-header">
                  <div>
                    <p className="explorer-kicker">Supporting literature</p>
                    <h2 className="text-xl font-semibold">Citations</h2>
                  </div>
                </div>
                <div className="space-y-3">
                  {explorer.citations.map((citation) => (
                    <article key={`${citation.title}-${citation.doi ?? citation.url ?? 'citation'}`} className="rounded-[1.25rem] border border-border bg-white/80 p-4">
                      <p className="font-medium">{citation.title}</p>
                      <p className="mt-2 text-sm text-muted-foreground">{citation.authors.join(', ')} {citation.year ? `(${citation.year})` : ''}</p>
                      {citation.url && (
                        <a
                          href={citation.url}
                          target="_blank"
                          rel="noreferrer"
                          className="mt-3 inline-flex items-center gap-2 text-xs uppercase tracking-[0.18em] text-muted-foreground hover:text-foreground"
                        >
                          Open source
                          <ExternalLink className="h-3.5 w-3.5" />
                        </a>
                      )}
                    </article>
                  ))}
                </div>
              </section>
            )}
          </aside>
        )}
      </div>

      {isMobile && (
        <Drawer open={drawerOpen} onOpenChange={setDrawerOpen}>
          <DrawerContent className="max-h-[82vh] overflow-y-auto bg-[#f5f0e6]">
            <DrawerHeader>
              <DrawerTitle>{evidenceTitle}</DrawerTitle>
              <DrawerDescription>Evidence and extraction details for the current selection.</DrawerDescription>
            </DrawerHeader>
            <div className="px-4 pb-6">
              <EvidencePanel evidence={activeEvidence} title={evidenceTitle} />
            </div>
          </DrawerContent>
        </Drawer>
      )}

      <div className="rounded-[1.5rem] border border-border bg-white/70 p-4 text-xs text-muted-foreground">
        Protocol slug: <span className="font-mono text-foreground">{slug}</span>
      </div>
    </div>
  );
}
