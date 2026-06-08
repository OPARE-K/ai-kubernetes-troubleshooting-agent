export interface HealthResponse {
  status: string;
  service: string;
}

export interface InvestigationPayload {
  pods: Record<string, unknown>;
  logs: Record<string, unknown>;
  events: Record<string, unknown>;
  deployments: Record<string, unknown>;
  network: Record<string, unknown>;
}

export interface Diagnosis {
  root_cause: string;
  explanation: string;
  fix: string;
  kubectl_command: string;
  kubectl_commands?: string[];
  command?: string;
  prevention_recommendation?: string;
  confidence: number;
  confidence_reasoning?: string;
}

export interface ClusterInfo {
  name: string;
  is_current: boolean;
  reachable: boolean;
  status_message: string;
}

export interface ClustersResponse {
  configured: boolean;
  path: string;
  message: string;
  current_context: string | null;
  clusters: ClusterInfo[];
}

export interface InvestigateResponse {
  status: string;
  investigation: InvestigationPayload;
  diagnosis: Diagnosis;
  warnings?: string[];
  cluster_healthy?: boolean | null;
  cluster_context?: string | null;
}

export interface InvestigationRecord {
  id: string;
  user_id: string;
  root_cause: string | null;
  namespace: string | null;
  confidence: number | null;
  status: string;
  diagnosis: Diagnosis | null;
  investigation: InvestigationPayload | null;
  created_at: string;
}

export interface ProgressEvent {
  step: string;
  status: "running" | "complete";
}

export const INVESTIGATION_STEPS = [
  { id: "checking_pods", label: "Checking Pods" },
  { id: "reading_logs", label: "Reading Logs" },
  { id: "analyzing_events", label: "Analyzing Events" },
  { id: "inspecting_deployments", label: "Inspecting Deployments" },
  { id: "checking_networking", label: "Checking Networking" },
  { id: "ai_reasoning", label: "AI Reasoning" },
  { id: "root_cause_found", label: "Root Cause Found" },
] as const;
