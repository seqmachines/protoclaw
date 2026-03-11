import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertCircle, ExternalLink, UploadCloud } from 'lucide-react';

import { ErrorState, EmptyState, LoadingState } from '@/components/States';
import { SubmissionStatusBadge } from '@/components/StatusBadge';
import { api, Submission } from '@/lib/api';

function formatDate(dateStr?: string | null) {
  if (!dateStr) {
    return '-';
  }

  try {
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(dateStr));
  } catch {
    return dateStr;
  }
}

function truncateSource(url: string, limit = 88) {
  if (url.length <= limit) {
    return url;
  }

  try {
    const parsed = new URL(url);
    return `${parsed.hostname}${parsed.pathname.slice(0, 42)}...`;
  } catch {
    return `${url.slice(0, limit)}...`;
  }
}

export default function SubmissionsPage() {
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.submissions
      .list()
      .then(setSubmissions)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const counts = useMemo(
    () =>
      submissions.reduce<Record<string, number>>((accumulator, submission) => {
        accumulator[submission.status] = (accumulator[submission.status] ?? 0) + 1;
        return accumulator;
      }, {}),
    [submissions],
  );

  return (
    <div>
      <div className="page-header">
        <div className="flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center border border-border bg-card">
            <UploadCloud className="h-5 w-5" />
          </span>
          <div>
            <p className="font-mono text-[11px] uppercase tracking-[0.24em] text-muted-foreground">Ingestion queue</p>
            <h1 className="text-2xl font-semibold tracking-[0.04em]">Submissions</h1>
          </div>
          {!loading && !error && <span className="stat-pill">{submissions.length} items</span>}
        </div>
        <p className="max-w-3xl text-sm text-muted-foreground">
          Monitor uploaded files and source URLs, inspect failures, and see which submissions were promoted into
          published protocol records.
        </p>
      </div>

      {!loading && !error && submissions.length > 0 && (
        <section className="section-card mb-5">
          <div className="flex flex-wrap gap-2">
            {Object.entries(counts).map(([status, count]) => (
              <div key={status} className="inline-flex items-center gap-2 border border-border bg-background px-3 py-2">
                <SubmissionStatusBadge status={status} />
                <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">{count}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      {loading && <LoadingState />}
      {error && <ErrorState error={error} />}
      {!loading && !error && submissions.length === 0 && <EmptyState message="No submissions found." />}

      {!loading && !error && submissions.length > 0 && (
        <>
          <section className="hidden overflow-hidden border border-border bg-card md:block">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-background/70">
                  <th className="px-4 py-3 text-left font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Source</th>
                  <th className="px-4 py-3 text-left font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Status</th>
                  <th className="px-4 py-3 text-left font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Protocol</th>
                  <th className="px-4 py-3 text-left font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Run stage</th>
                  <th className="px-4 py-3 text-left font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Review</th>
                  <th className="px-4 py-3 text-left font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Created</th>
                  <th className="px-4 py-3 text-left font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Error</th>
                </tr>
              </thead>
              <tbody>
                {submissions.map((submission) => (
                  <tr key={submission.id} className="border-b border-border/70 last:border-0">
                    <td className="px-4 py-4 align-top">
                      <a
                        href={submission.source_url}
                        target="_blank"
                        rel="noreferrer"
                        title={submission.source_url}
                        className="inline-flex items-start gap-1 text-xs text-foreground hover:text-muted-foreground"
                      >
                        <span className="max-w-md break-all font-mono">{truncateSource(submission.source_url)}</span>
                        <ExternalLink className="mt-0.5 h-3 w-3 shrink-0" />
                      </a>
                    </td>
                    <td className="px-4 py-4 align-top">
                      <SubmissionStatusBadge status={submission.status} />
                    </td>
                    <td className="px-4 py-4 align-top font-mono text-xs text-muted-foreground">
                      {submission.protocol_slug ?? '-'}
                    </td>
                    <td className="px-4 py-4 align-top font-mono text-xs text-muted-foreground">
                      {submission.latest_run?.stage ?? '-'}
                    </td>
                    <td className="px-4 py-4 align-top">
                      {submission.review_request_id ? (
                        <Link
                          to={`/reviews/${submission.review_request_id}`}
                          className="inline-flex items-center gap-1 text-xs uppercase tracking-[0.18em] text-foreground hover:text-muted-foreground"
                        >
                          compare
                        </Link>
                      ) : (
                        <span className="text-muted-foreground">-</span>
                      )}
                    </td>
                    <td className="px-4 py-4 align-top text-xs text-muted-foreground">
                      {formatDate(submission.created_at)}
                    </td>
                    <td className="px-4 py-4 align-top">
                      {submission.error_message ? (
                        <div className="flex max-w-sm items-start gap-2 border border-destructive/20 bg-destructive/10 px-3 py-2">
                          <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-destructive" />
                          <p className="text-xs text-muted-foreground">{submission.error_message}</p>
                        </div>
                      ) : (
                        <span className="text-muted-foreground">-</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <section className="space-y-3 md:hidden">
            {submissions.map((submission) => (
              <article key={submission.id} className="section-card space-y-3">
                <div className="flex items-start justify-between gap-3">
                  <a
                    href={submission.source_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-start gap-1 text-xs text-foreground hover:text-muted-foreground"
                  >
                    <span className="break-all font-mono">{truncateSource(submission.source_url, 56)}</span>
                    <ExternalLink className="mt-0.5 h-3 w-3 shrink-0" />
                  </a>
                  <SubmissionStatusBadge status={submission.status} />
                </div>

                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="border border-border bg-background p-3">
                    <p className="data-label mb-2">Protocol</p>
                    <p className="font-mono text-xs text-muted-foreground">{submission.protocol_slug ?? '-'}</p>
                  </div>
                  <div className="border border-border bg-background p-3">
                    <p className="data-label mb-2">Created</p>
                    <p className="text-xs text-muted-foreground">{formatDate(submission.created_at)}</p>
                  </div>
                  <div className="border border-border bg-background p-3">
                    <p className="data-label mb-2">Run stage</p>
                    <p className="font-mono text-xs text-muted-foreground">{submission.latest_run?.stage ?? '-'}</p>
                  </div>
                  <div className="border border-border bg-background p-3">
                    <p className="data-label mb-2">Review</p>
                    {submission.review_request_id ? (
                      <Link to={`/reviews/${submission.review_request_id}`} className="font-mono text-xs text-foreground hover:text-muted-foreground">
                        open comparison
                      </Link>
                    ) : (
                      <p className="font-mono text-xs text-muted-foreground">-</p>
                    )}
                  </div>
                  <div className="border border-border bg-background p-3">
                    <p className="data-label mb-2">Submitted by</p>
                    <p className="font-mono text-xs text-muted-foreground">{submission.submitted_by ?? '-'}</p>
                  </div>
                </div>

                {submission.error_message && (
                  <div className="flex items-start gap-2 border border-destructive/20 bg-destructive/10 px-3 py-3">
                    <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
                    <p className="text-xs text-muted-foreground">{submission.error_message}</p>
                  </div>
                )}
              </article>
            ))}
          </section>

          <p className="mt-3 font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
            {submissions.length} total submissions
          </p>
        </>
      )}
    </div>
  );
}
