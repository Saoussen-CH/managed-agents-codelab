import type { AppConfig, AgentRecord, RunRecord } from "./types";

const BASE = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const getConfig = () => request<AppConfig>("/config");
export const updateConfig = (updates: Partial<AppConfig>) =>
  request<AppConfig>("/config", { method: "PUT", body: JSON.stringify(updates) });

export const listAgents = () => request<AgentRecord[]>("/agents");
export const createAgent = (body: { id: string; description: string }) =>
  request<AgentRecord>("/agents", { method: "POST", body: JSON.stringify(body) });
export const getAgent = (id: string) => request<AgentRecord>(`/agents/${id}`);
export const deleteAgent = (id: string) =>
  request<void>(`/agents/${id}`, { method: "DELETE" });

export const startRun = (agent_id?: string) =>
  request<{ run_id: string }>("/runs", {
    method: "POST",
    body: JSON.stringify({ agent_id: agent_id ?? null }),
  });
export const listRuns = () => request<RunRecord[]>("/runs");
export const getRun = (id: string) => request<RunRecord>(`/runs/${id}`);
export const startRefine = (run_id: string, message: string) =>
  request<{ run_id: string }>(`/runs/${run_id}/refine`, {
    method: "POST",
    body: JSON.stringify({ message }),
  });
export const getPdfUrl = (run_id: string) => `${BASE}/runs/${run_id}/pdf`;
