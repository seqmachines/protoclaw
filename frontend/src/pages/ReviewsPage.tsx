import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { GitCompareArrows, ChevronRight, ExternalLink } from 'lucide-react';

import { ErrorState, EmptyState, LoadingState } from '@/components/States';
import { ConfidenceScore, ReviewStatusBadge } from '@/components/StatusBadge';
import { api, type ReviewListItem } from '@/lib/api';

function formatDate(value?: string | null) {
  if (!value) return '-';
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value));
}

export default function ReviewsPage() {
  const navigate = useNavigate();
  const [reviews, setReviews] = useState<ReviewListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.reviews
      .list()
      .then(setReviews)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <div className="page-header">
        <div className="flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center border border-border bg-card">
            <GitCompareArrows className="h-5 w-5" />
          </span>
          <div>
            <p className="font-mono text-[11px] uppercase tracking-[0.24em] text-muted-foreground">Review queue</p>
            <h1 className="text-2xl font-semibold tracking-[0.04em]">Pending reviews</h1>
          </div>
          {!loading && !error && <span className="stat-pill">{reviews.length} items</span>}
        </div>
        <p className="max-w-3xl text-sm text-muted-foreground">
          Review duplicate submissions and draft updates before they replace the canonical protocol record.
        </p>
      </div>

      {loading && <LoadingState />}
      {error && <ErrorState error={error} />}
      {!loading && !error && reviews.length === 0 && <EmptyState message="No pending reviews." />}

      {!loading && !error && reviews.length > 0 && (
        <section className="hidden overflow-hidden border border-border bg-card md:block">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-background/70">
                <th className="px-4 py-3 text-left font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Protocol</th>
                <th className="px-4 py-3 text-left font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Type</th>
                <th className="px-4 py-3 text-left font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Confidence</th>
                <th className="px-4 py-3 text-left font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Created</th>
                <th className="px-4 py-3 text-left font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Source</th>
                <th className="w-8 px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {reviews.map((review) => (
                <tr
                  key={review.id}
                  className="table-row-hover border-b border-border/70 last:border-0"
                  onClick={() => navigate(`/reviews/${review.id}`)}
                >
                  <td className="px-4 py-4 align-top">
                    <div className="space-y-1">
                      <p className="font-medium">{review.protocol_name ?? review.protocol_slug ?? review.id}</p>
                      {review.protocol_slug && <p className="font-mono text-xs text-muted-foreground">{review.protocol_slug}</p>}
                    </div>
                  </td>
                  <td className="px-4 py-4 align-top">
                    <div className="flex flex-wrap gap-2">
                      <ReviewStatusBadge status={review.status} />
                      <span className="stat-pill">{review.duplicate_submission ? 'duplicate draft' : 'review'}</span>
                    </div>
                  </td>
                  <td className="px-4 py-4 align-top"><ConfidenceScore score={review.confidence_score} /></td>
                  <td className="px-4 py-4 align-top text-xs text-muted-foreground">{formatDate(review.created_at)}</td>
                  <td className="px-4 py-4 align-top">
                    {review.source_url ? (
                      <a href={review.source_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground">
                        source
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    ) : (
                      <span className="text-muted-foreground">-</span>
                    )}
                  </td>
                  <td className="px-4 py-4 align-top text-muted-foreground"><ChevronRight className="h-4 w-4" /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}
