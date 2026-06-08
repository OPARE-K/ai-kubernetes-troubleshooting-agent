"use client";

import type { ClusterInfo } from "@/types/api";

export function ClusterPicker({
  clusters,
  selectedContext,
  isLoading,
  error,
  kubeconfigPath,
  onSelect,
  onRefresh,
}: {
  clusters: ClusterInfo[];
  selectedContext: string | null;
  isLoading: boolean;
  error: string | null;
  kubeconfigPath: string;
  onSelect: (context: string) => void;
  onRefresh: () => void;
}) {
  if (isLoading) {
    return (
      <section className="glass-card animate-fade-in p-6">
        <h2 className="section-title">Kubernetes Clusters</h2>
        <div className="mt-4 space-y-3">
          <div className="skeleton-line w-3/4" />
          <div className="skeleton-line w-1/2" />
        </div>
        <p className="mt-4 text-sm text-slate-500">Loading clusters from kubeconfig...</p>
      </section>
    );
  }

  if (error) {
    return (
      <section className="glass-card animate-fade-in border-red-500/20 p-6">
        <h2 className="section-title">Kubernetes Clusters</h2>
        <div className="alert-error mt-4 whitespace-pre-line">{error}</div>
        <button type="button" onClick={onRefresh} className="btn-secondary mt-4">
          Retry
        </button>
      </section>
    );
  }

  if (clusters.length === 0) {
    return (
      <section className="glass-card animate-fade-in border-amber-500/20 p-6">
        <h2 className="section-title">Kubernetes Clusters</h2>
        <div className="alert-warning mt-4 whitespace-pre-line">
          No clusters found in kubeconfig.
          {kubeconfigPath ? `\n\nPath: ${kubeconfigPath}` : ""}
          {"\n\n"}Please verify kubeconfig path and cluster contexts.
        </div>
        <button type="button" onClick={onRefresh} className="btn-secondary mt-4">
          Refresh
        </button>
      </section>
    );
  }

  return (
    <section className="glass-card animate-fade-in p-6">
      <div className="mb-5 flex items-start justify-between gap-4">
        <div>
          <h2 className="section-title">Kubernetes Clusters</h2>
          <p className="section-subtitle mt-1">
            Select a cluster from your kubeconfig to investigate.
          </p>
        </div>
        <button type="button" onClick={onRefresh} className="btn-secondary shrink-0">
          Refresh
        </button>
      </div>
      <ul className="grid gap-3 sm:grid-cols-2">
        {clusters.map((cluster) => {
          const selected = cluster.name === selectedContext;
          return (
            <li key={cluster.name}>
              <button
                type="button"
                onClick={() => onSelect(cluster.name)}
                className={`group w-full rounded-xl border p-4 text-left transition-all duration-200 ${
                  selected
                    ? "border-sky-500/60 bg-sky-500/10 shadow-glow ring-1 ring-sky-500/30"
                    : "border-white/10 bg-slate-950/40 hover:border-white/20 hover:bg-slate-900/60"
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <span className="block truncate font-medium text-white">{cluster.name}</span>
                    {cluster.is_current ? (
                      <p className="mt-1 text-xs text-slate-500">Current kubeconfig context</p>
                    ) : null}
                  </div>
                  <span
                    className={`badge shrink-0 ${
                      cluster.reachable
                        ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                        : "border-amber-500/30 bg-amber-500/10 text-amber-300"
                    }`}
                  >
                    {cluster.reachable ? "Reachable" : "Unreachable"}
                  </span>
                </div>
                {!cluster.reachable && cluster.status_message ? (
                  <p className="mt-3 line-clamp-3 text-xs leading-relaxed text-amber-200/80">
                    {cluster.status_message}
                  </p>
                ) : null}
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
