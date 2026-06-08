"use client";

import { useState } from "react";

import { ClusterPicker } from "@/components/ClusterPicker";
import { DiagnosisCard } from "@/components/DiagnosisCard";
import { InvestigationHistory } from "@/components/InvestigationHistory";
import { InvestigationProgress } from "@/components/InvestigationProgress";
import { useAuth } from "@/contexts/AuthContext";
import { useClusters } from "@/hooks/useClusters";
import { useInvestigationHistory } from "@/hooks/useInvestigationHistory";
import { useInvestigationRealtime } from "@/hooks/useInvestigationRealtime";
import { parseApiError } from "@/lib/apiErrors";
import { runInvestigation } from "@/services/api";
import type { Diagnosis } from "@/types/api";

export function Dashboard() {
  const { user, signOut } = useAuth();
  const { history, isLoading, reloadHistory } = useInvestigationHistory();
  const {
    clusters,
    kubeconfigPath,
    isLoading: clustersLoading,
    error: clustersError,
    selectedContext,
    setSelectedContext,
    reload: reloadClusters,
  } = useClusters();
  const [investigationId, setInvestigationId] = useState<string | null>(null);
  const [isInvestigating, setIsInvestigating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [diagnosis, setDiagnosis] = useState<Diagnosis | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [clusterHealthy, setClusterHealthy] = useState<boolean | null>(null);
  const [activeClusterContext, setActiveClusterContext] = useState<string | null>(null);
  const { steps } = useInvestigationRealtime(investigationId);
  const displaySteps = diagnosis
    ? steps.map((step) => ({ ...step, status: "complete" as const }))
    : steps;

  const selectedCluster = clusters.find((cluster) => cluster.name === selectedContext);

  const handleInvestigate = async () => {
    if (!selectedContext) {
      setError("Select a Kubernetes cluster before investigating.");
      return;
    }

    const id = crypto.randomUUID();
    setInvestigationId(id);
    setIsInvestigating(true);
    setError(null);
    setDiagnosis(null);
    setWarnings([]);
    setClusterHealthy(null);
    setActiveClusterContext(selectedContext);

    try {
      if (!user?.id) {
        throw new Error("You must be signed in to investigate.");
      }

      const result = await runInvestigation(id, user.id, selectedContext);
      setDiagnosis(result.diagnosis);
      setWarnings(result.warnings ?? []);
      setClusterHealthy(result.cluster_healthy ?? null);
      setActiveClusterContext(result.cluster_context ?? selectedContext);
      await reloadHistory();
    } catch (err) {
      setError(
        parseApiError(
          err,
          "Investigation failed. Check backend connectivity and try again."
        )
      );
    } finally {
      setIsInvestigating(false);
    }
  };

  return (
    <main className="app-background min-h-screen text-white">
      <div className="mx-auto max-w-5xl px-6 py-10">
        <header className="mb-10 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="animate-fade-in">
            <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-sky-500/20 bg-sky-500/10 px-3 py-1 text-xs font-medium text-sky-300">
              <span className="h-1.5 w-1.5 rounded-full bg-sky-400" />
              Kubernetes Troubleshooting
            </div>
            <h1 className="bg-gradient-to-r from-white via-slate-100 to-slate-300 bg-clip-text text-3xl font-bold tracking-tight text-transparent sm:text-4xl">
              AI Kubernetes Agent
            </h1>
            <p className="mt-2 text-sm text-slate-400">
              Signed in as <span className="text-slate-200">{user?.email}</span>
            </p>
          </div>
          <button type="button" onClick={() => signOut()} className="btn-secondary self-start">
            Sign out
          </button>
        </header>

        <div className="space-y-6">
          <ClusterPicker
            clusters={clusters}
            selectedContext={selectedContext}
            isLoading={clustersLoading}
            error={clustersError}
            kubeconfigPath={kubeconfigPath}
            onSelect={setSelectedContext}
            onRefresh={reloadClusters}
          />

          <section className="glass-card-accent animate-fade-in p-8 text-center">
            <button
              type="button"
              onClick={handleInvestigate}
              disabled={
                isInvestigating || clustersLoading || !selectedContext || !selectedCluster?.reachable
              }
              className="btn-primary min-w-[240px] px-10"
            >
              {isInvestigating ? (
                <span className="inline-flex items-center gap-2">
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                  Investigating Kubernetes Cluster...
                </span>
              ) : selectedContext ? (
                `Investigate ${selectedContext}`
              ) : (
                "Investigate Cluster"
              )}
            </button>
            {selectedCluster && !selectedCluster.reachable ? (
              <div className="alert-warning mx-auto mt-4 max-w-xl whitespace-pre-line text-left">
                Selected cluster is unreachable. Choose another cluster or fix kubeconfig access.
              </div>
            ) : null}
            {error ? (
              <div className="alert-error mx-auto mt-4 max-w-xl whitespace-pre-line text-left">
                {error}
              </div>
            ) : null}
          </section>

          <InvestigationProgress
            steps={displaySteps}
            isActive={isInvestigating || !!diagnosis}
            title={
              isInvestigating
                ? "Investigating Kubernetes Cluster..."
                : "Investigation Status"
            }
          />
          <DiagnosisCard
            diagnosis={diagnosis}
            clusterHealthy={clusterHealthy}
            warnings={warnings}
            clusterContext={activeClusterContext}
          />
          <InvestigationHistory history={history} isLoading={isLoading} />
        </div>
      </div>
    </main>
  );
}
