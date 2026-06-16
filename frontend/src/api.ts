import type {
  AIModelRun,
  ChatAction,
  DeviceSummary,
  LogAnalysis,
  PayloadDetail,
  RiskAssessment,
  TimelineItem
} from "./types";

const DEFAULT_API_URL = import.meta.env.VITE_AEGIS_API_URL || "http://127.0.0.1:8080/api/v1";

export class AegisApi {
  baseUrl: string;
  token: string;

  constructor(baseUrl = DEFAULT_API_URL, token = "sample-token") {
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.token = token;
  }

  async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${this.token}`,
        ...(init.headers || {})
      }
    });
    if (!response.ok) {
      const body = await response.text();
      throw new Error(`${response.status} ${response.statusText}: ${body}`);
    }
    return response.json() as Promise<T>;
  }

  devices() {
    return this.request<{ items: DeviceSummary[] }>("/devices");
  }

  latestRisk(deviceId: string) {
    return this.request<RiskAssessment>(`/devices/${encodeURIComponent(deviceId)}/latest-risk`);
  }

  timeline(deviceId: string) {
    return this.request<{ device_id: string; items: TimelineItem[] }>(
      `/devices/${encodeURIComponent(deviceId)}/timeline?limit=12`
    );
  }

  payload(payloadId: string) {
    return this.request<PayloadDetail>(`/payloads/${encodeURIComponent(payloadId)}`);
  }

  logs(deviceId?: string) {
    const query = deviceId ? `?device_id=${encodeURIComponent(deviceId)}&limit=30` : "?limit=30";
    return this.request<LogAnalysis>(`/logs/analysis${query}`);
  }

  aiRuns(deviceId?: string) {
    const query = deviceId ? `?device_id=${encodeURIComponent(deviceId)}&limit=20` : "?limit=20";
    return this.request<{ items: AIModelRun[] }>(`/ai/runs${query}`);
  }

  async createChatSession(title: string) {
    return this.request<{ id: string; title: string; created_at: string }>("/chat/sessions", {
      method: "POST",
      body: JSON.stringify({ title })
    });
  }

  async sendChatMessage(sessionId: string, content: string, contextPayloadId?: string) {
    return this.request<{
      message: { id: string; content: string; role: "assistant" };
      actions: ChatAction[];
      route?: string;
      safety?: Record<string, unknown>;
    }>(`/chat/sessions/${encodeURIComponent(sessionId)}/messages`, {
      method: "POST",
      body: JSON.stringify({ content, context_payload_id: contextPayloadId || null })
    });
  }

  confirmAction(actionId: string) {
    return this.request<ChatAction>(`/chat/actions/${encodeURIComponent(actionId)}/confirm`, {
      method: "POST",
      body: JSON.stringify({})
    });
  }
}
