import { ApiError, apiRequest } from "./client";

export interface AssistantAttachment { id: string; name: string; mimeType: string; url: string; }
export interface AssistantMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  attachments: AssistantAttachment[];
  sourceRefs?: Array<{ label?: string; url?: string; status?: string; error?: string }>;
}
export interface FieldPatch { path: string; label: string; value: unknown; confidence: number; sourceRefs?: string[]; status: "pending" | "applied" | "ignored"; }
export interface SuggestionRun { id: string; patches: FieldPatch[]; appliedFields: string[]; ignoredFields: string[]; source?: "deepseek" | "rule"; }
export interface AssistantThread { id: string; giftId?: string | null; messages: AssistantMessage[]; suggestionRuns: SuggestionRun[]; }
export interface AssistantTurn { userMessage: AssistantMessage; assistantMessage: AssistantMessage; suggestionRun: SuggestionRun; }
export interface BatchLinkItem {
  url: string;
  status: string;
  suggestedName: string;
  patches: FieldPatch[];
  duplicates: Array<{ gift_id?: string; canonical_name: string; exact: boolean; similarity: number }>;
  questions?: string[];
}

export function createAssistantThread(draftId: string, giftId?: string | null) {
  return apiRequest<AssistantThread>("/api/ai/threads", { method: "POST", body: { draftId, giftId } });
}

export function sendAssistantMessage(threadId: string, payload: { content: string; giftTypeCode: string; currentValues: unknown; attachments: AssistantAttachment[] }) {
  return apiRequest<AssistantTurn>(`/api/ai/threads/${threadId}/messages`, { method: "POST", body: payload });
}

export async function uploadAssistantAttachment(threadId: string, file: File): Promise<AssistantAttachment> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`/api/ai/threads/${threadId}/attachments`, { method: "POST", body: form, credentials: "include" });
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: string } | null;
    throw new ApiError(payload?.detail || "图片上传失败", response.status, payload?.detail);
  }
  return response.json();
}

export function reviewSuggestionRun(runId: string, appliedFields: string[], ignoredFields: string[]) {
  return apiRequest<SuggestionRun>(`/api/ai/suggestion-runs/${runId}`, { method: "PATCH", body: { appliedFields, ignoredFields } });
}

export function bindAssistantThread(threadId: string, giftId: string) {
  return apiRequest<AssistantThread>(`/api/ai/threads/${threadId}/bind`, { method: "PATCH", body: { giftId } });
}

export function analyzeBatchLinks(urls: string[], giftTypeCode: string) {
  return apiRequest<{ items: BatchLinkItem[]; count: number }>("/api/ai/batch-links", {
    method: "POST",
    body: { urls, giftTypeCode },
  });
}
