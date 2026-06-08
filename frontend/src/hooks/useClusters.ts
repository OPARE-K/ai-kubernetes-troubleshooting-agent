"use client";

import { useCallback, useEffect, useState } from "react";

import { parseApiError } from "@/lib/apiErrors";
import { fetchClusters } from "@/services/api";
import type { ClusterInfo, ClustersResponse } from "@/types/api";

export function useClusters() {
  const [data, setData] = useState<ClustersResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedContext, setSelectedContext] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetchClusters();
      setData(response);
      if (!response.configured) {
        setError(response.message || "Kubeconfig is not configured.");
      } else if (response.clusters.length === 0 && response.message) {
        setError(response.message);
      }
      setSelectedContext((current) => {
        if (current && response.clusters.some((cluster) => cluster.name === current)) {
          return current;
        }
        const currentCluster = response.clusters.find((cluster) => cluster.is_current);
        return currentCluster?.name ?? response.clusters[0]?.name ?? null;
      });
    } catch (err) {
      setError(parseApiError(err, "Failed to load clusters from kubeconfig."));
      setData(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  const clusters: ClusterInfo[] = data?.clusters ?? [];

  return {
    clusters,
    kubeconfigPath: data?.path ?? "",
    kubeconfigConfigured: data?.configured ?? false,
    currentContext: data?.current_context ?? null,
    isLoading,
    error,
    selectedContext,
    setSelectedContext,
    reload,
  };
}
