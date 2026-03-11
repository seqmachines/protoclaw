import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

import { ProtocolExplorerView } from '@/components/ProtocolExplorer';
import { ErrorState, LoadingState } from '@/components/States';
import { api, type ProtocolExplorer } from '@/lib/api';

type ResourceState<T> = {
  data: T | null;
  loading: boolean;
  error: string | null;
};

function createIdleState<T>(): ResourceState<T> {
  return { data: null, loading: true, error: null };
}

export default function ProtocolDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const [protocol, setProtocol] = useState<ResourceState<ProtocolExplorer>>(createIdleState());

  useEffect(() => {
    if (!slug) {
      return;
    }

    setProtocol(createIdleState());

    api.protocols
      .explorer(slug)
      .then((data) => setProtocol({ data, loading: false, error: null }))
      .catch((error: Error) => setProtocol({ data: null, loading: false, error: error.message }));
  }, [slug]);

  return (
    <div>
      <Link
        to="/"
        className="mb-6 inline-flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to protocols
      </Link>

      {protocol.loading && <LoadingState />}
      {!protocol.loading && protocol.error && <ErrorState error={protocol.error} />}
      {!protocol.loading && protocol.data && slug && <ProtocolExplorerView slug={slug} explorer={protocol.data} />}
    </div>
  );
}
