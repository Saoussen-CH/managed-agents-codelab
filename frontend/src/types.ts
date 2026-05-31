export interface AppConfig {
  sources: string[];
  voice: string;
  agents_md: string;
  skill_md: string;
}

export type RunStatus = "running" | "completed" | "failed";

export interface RunRecord {
  id: string;
  started_at: string;
  status: RunStatus;
  agent_id: string | null;
  environment_id: string | null;
  interaction_id: string | null;
  refine_interaction_id: string | null;
  output_text: string | null;
  refine_output_text: string | null;
  pdf_available: boolean;
  error: string | null;
}

export interface AgentRecord {
  id: string;
  description: string;
  base_agent: string;
}

export type SSEEventType = "step" | "output" | "done" | "error";

export interface SSEEvent {
  type: SSEEventType;
  content?: string;
  message?: string;
  pdf_available?: boolean;
  environment_id?: string;
  interaction_id?: string;
}
