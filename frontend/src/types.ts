export type RiskLabel = "Low" | "Medium" | "High" | "Critical" | "UNKNOWN" | string;

export type DeviceSummary = {
  device_id: string;
  payload_count: number;
  latest_risk_label: RiskLabel;
  latest_risk_score: number;
};

export type RiskAssessment = {
  payload_id: string;
  device_id: string;
  risk_score: number;
  risk_label: RiskLabel;
  confidence: number;
  reasons: string[];
  recommended_action: string;
  needs_human_review: boolean;
  created_at: string;
};

export type TimelineItem = {
  payload_id: string;
  device_id: string;
  scan_id: number;
  created_at_epoch_ms: number;
  processing_status: string;
  received_at: string;
  risk?: RiskAssessment | null;
  risk_score?: number;
  risk_label?: RiskLabel;
};

export type DeviceReport = {
  is_rooted: boolean;
  root_signal_count: number;
  play_integrity_status: string | null;
  security_patch_date: string | null;
  security_patch_age_days: number | null;
  bootloader_state: string | null;
};

export type ImportantLog = {
  id: number;
  payload_id: string;
  device_id?: string;
  observed_at_epoch_ms: number;
  tag: string;
  level: string;
  matched_rule: string;
  message_redacted: string;
  message_hash: string;
};

export type PayloadDetail = {
  payload_id: string;
  device_id: string;
  scan_id: number;
  processing_status: string;
  processing_error?: string | null;
  received_at: string;
  created_at_epoch_ms: number;
  device_report?: DeviceReport | null;
  risk?: RiskAssessment | null;
  apps: Array<{
    package_name: string;
    version_name?: string | null;
    install_source: string;
    is_system_app: boolean;
    requested_permissions: string[];
    is_suspicious: boolean;
  }>;
  logs: ImportantLog[];
  ai_runs: AIModelRun[];
  ai_decision?: AIRiskDecision | null;
  ai_evidence_bundles: AIEvidenceBundle[];
  ai_findings: AIFinding[];
};

export type LogAnalysis = {
  summary: {
    total_logs: number;
    affected_devices: number;
    high_severity_count: number;
    unique_message_hashes: number;
    repeated_clusters: number;
    threat_regex_count: number;
  };
  by_level: Record<string, number>;
  by_rule: Record<string, number>;
  top_tags: Array<{ tag: string; count: number }>;
  top_devices: Array<{ device_id: string; count: number }>;
  timeline: Array<{ day: string; total: number; high_severity: number }>;
  clusters: Array<{
    message_hash: string;
    count: number;
    devices: string[];
    tags: Record<string, number>;
    levels: Record<string, number>;
    sample_message: string;
  }>;
  recent_logs: ImportantLog[];
};

export type AIModelRun = {
  id: number;
  payload_id: string;
  model_role: string;
  provider: string;
  model_name: string;
  prompt_version: string;
  status: string;
  latency_ms: number;
  cost_estimate: number;
  output: Record<string, unknown>;
  created_at: string;
};

export type AIRiskDecision = {
  id?: number;
  payload_id?: string;
  device_id?: string;
  deterministic_score: number;
  deterministic_label: RiskLabel;
  final_score: number;
  final_label: RiskLabel;
  confidence: number;
  reasons: string[];
  evidence_refs: string[];
  recommended_action: string;
  used_ai_final: boolean;
  status: string;
  created_at: string;
};

export type AIEvidenceBundle = {
  id: number;
  bundle_stage: string;
  bundle_hash: string;
  router_path: string;
  bundle: {
    router_decision?: {
      path: string;
      roles: string[];
      needs_reviewer: boolean;
      reasons: string[];
    };
    evidence_refs?: string[];
    suspicious_app_count?: number;
    log_signal_count?: number;
    risk?: {
      score: number;
      label: string;
    };
  } & Record<string, unknown>;
  created_at: string;
};

export type AIFinding = {
  id: number;
  model_run_id?: number | null;
  source_role: string;
  title: string;
  severity: string;
  confidence: number;
  reason: string;
  evidence_refs: string[];
  status: string;
  created_at: string;
};

export type ChatAction = {
  id: string;
  tool_name: string;
  status: string;
  payload: Record<string, unknown>;
  result?: Record<string, unknown> | null;
};

export type ChatMessage = {
  id?: string;
  role: "user" | "assistant";
  content: string;
};
