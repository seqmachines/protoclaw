import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, ExternalLink, GitCompareArrows } from 'lucide-react';

import { ErrorState, LoadingState } from '@/components/States';
import { ConfidenceScore, ReviewStatusBadge } from '@/components/StatusBadge';
import { Button } from '@/components/ui/button';
import { api, type ReviewComparison, type ReviewStatus } from '@/lib/api';

type ResourceState<T> = {
  data: T | null;
  loading: boolean;
  error: string | null;
};

function createIdleState<T>(): ResourceState<T> {
  return { data: null, loading: true, error: null };
}

function serializeValue(value: unknown) {
  if (value == null) return '-';
  if (typeof value === 'string') return value;
  return JSON.stringify(value, null, 2);
}

export default function ReviewDetailPage() {
  const { reviewId } = useParams<{ reviewId: string }>();
  const navigate = useNavigate();
  const [comparison, setComparison] = useState<ResourceState<ReviewComparison>>(createIdleState());
  const [decisionPending, setDecisionPending] = useState<ReviewStatus | null>(null);

  useEffect(() => {
    if (!reviewId) return;
    setComparison(createIdleState());
    api.reviews
      .comparison(reviewId)
      .then((data) => setComparison({ data, loading: false, error: null }))
      .catch((error: Error) => setComparison({ data: null, loading: false, error: error.message }));
  }, [reviewId]);

  const protocolSlug = comparison.data?.current_protocol.slug;
  const diffCount = comparison.data?.diffs.length ?? 0;

  async function handleDecision(decision: ReviewStatus) {
    if (!reviewId || !comparison.data) return;
    setDecisionPending(decision);
    try {
      await api.reviews.decide(reviewId, { decision });
      if (decision === 'approved' && protocolSlug) {
        navigate(`/protocols/${protocolSlug}`);
        return;
      }
      navigate('/reviews');
    } catch (error) {
      setComparison((current) => ({
        ...current,
        error: error instanceof Error ? error.message : 'Failed to save review decision.',
      }));
    } finally {
      setDecisionPending(null);
    }
  }

  const changedFields = useMemo(() => comparison.data?.diffs ?? [], [comparison.data]);

  return (
    <div>
      <Link
        to="/reviews"
        className="mb-6 inline-flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to reviews
      </Link>

      {comparison.loading && <LoadingState />}
      {!comparison.loading && comparison.error && <ErrorState error={comparison.error} />}

      {!comparison.loading && comparison.data && (
        <div className="space-y-6">
          <section className="explorer-hero">
            <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
              <div>
                <p className="explorer-kicker">Draft comparison</p>
                <div className="mt-3 flex flex-wrap items-center gap-3">
                  <h1 className="text-3xl font-semibold tracking-[-0.03em] text-[#12202f]">
                    {comparison.data.current_protocol.name}
                  </h1>
                  <ReviewStatusBadge status={comparison.data.review.status} />
                  <ConfidenceScore score={comparison.data.review.confidence_score} />
                  <span className="stat-pill">{comparison.data.review.duplicate_submission ? 'duplicate submission' : 'review'}</span>
                </div>
                {comparison.data.review.extraction_notes && (
                  <p className="mt-4 max-w-3xl text-sm text-muted-foreground">
                    {comparison.data.review.extraction_notes}
                  </p>
                )}
              </div>

              <div className="flex flex-wrap gap-2">
                <Button
                  className="rounded-full bg-[#1c2b37] px-5 text-xs uppercase tracking-[0.16em] text-white hover:bg-[#273947]"
                  disabled={decisionPending !== null}
                  onClick={() => handleDecision('approved')}
                >
                  {decisionPending === 'approved' ? 'Approving…' : 'Approve changes'}
                </Button>
                <Button
                  variant="outline"
                  className="rounded-full px-5 text-xs uppercase tracking-[0.16em]"
                  disabled={decisionPending !== null}
                  onClick={() => handleDecision('rejected')}
                >
                  {decisionPending === 'rejected' ? 'Rejecting…' : 'Reject'}
                </Button>
              </div>
            </div>
          </section>

          <section className="explorer-panel">
            <div className="explorer-panel-header">
              <div>
                <p className="explorer-kicker">Overview</p>
                <h2 className="text-xl font-semibold">{diffCount} changed fields</h2>
              </div>
              {comparison.data.review.source_url && (
                <a
                  href={comparison.data.review.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-2 text-xs uppercase tracking-[0.18em] text-muted-foreground hover:text-foreground"
                >
                  Open source
                  <ExternalLink className="h-3.5 w-3.5" />
                </a>
              )}
            </div>

            <div className="grid gap-3 lg:grid-cols-2">
              {changedFields.map((diff) => (
                <article key={diff.field} className="rounded-[1.25rem] border border-border bg-white/80 p-4">
                  <div className="mb-4 flex items-center gap-2">
                    <GitCompareArrows className="h-4 w-4 text-muted-foreground" />
                    <h3 className="font-semibold">{diff.field}</h3>
                  </div>
                  <div className="grid gap-3 xl:grid-cols-2">
                    <div className="rounded-xl border border-border bg-[#faf7f0] p-3">
                      <p className="data-label mb-2">Current</p>
                      <pre className="overflow-x-auto whitespace-pre-wrap break-words font-mono text-xs text-muted-foreground">
                        {serializeValue(diff.current_text ?? diff.current)}
                      </pre>
                    </div>
                    <div className="rounded-xl border border-border bg-[#eef6ff] p-3">
                      <p className="data-label mb-2">Draft</p>
                      <pre className="overflow-x-auto whitespace-pre-wrap break-words font-mono text-xs text-foreground">
                        {serializeValue(diff.draft_text ?? diff.draft)}
                      </pre>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
