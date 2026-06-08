import axios from "axios";

import type {
  ClustersResponse,
  HealthResponse,
  InvestigateResponse,
} from "@/types/api";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000",
  timeout: 600000,
});

export async function fetchHealth(): Promise<HealthResponse> {
  const { data } = await api.get<HealthResponse>("/health");
  return data;
}

export async function fetchClusters(): Promise<ClustersResponse> {
  const { data } = await api.get<ClustersResponse>("/clusters");
  return data;
}

export async function runInvestigation(
  investigationId: string,
  userId: string,
  clusterContext: string | null
): Promise<InvestigateResponse> {
  const { data } = await api.post<InvestigateResponse>("/investigate", {
    investigation_id: investigationId,
    user_id: userId,
    cluster_context: clusterContext,
  });
  return data;
}
