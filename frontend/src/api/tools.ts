import { apiRequest } from "./client";
import type { ActivityDetailsInput, GiftTypeCode, ProductDetailsInput } from "./gifts";

export interface CustomField { id: string; machineKey: string; displayName: string; description?: string; valueType: string; state: string; }
export interface TaobaoLoginSession { sessionId: string; ready: boolean; url: string; cookieCount: number; stateSaved: boolean; }
export interface ServerStatus {
  backend: { status: string; schemaVersion: number };
  deepseek: { configured: boolean; model: string };
  taobao: { enabled: boolean; browserAvailable: boolean; sessionActive: boolean; stateSaved: boolean };
}
export interface GiftAISuggestion {
  recommendedGiftTypeCode: GiftTypeCode;
  typeReason: string;
  subcategoryCode: string;
  shortDescription: string;
  whyTemplate: string;
  priceMin: number | null;
  priceMax: number | null;
  isFree: boolean;
  recipientTypes: string[];
  relationshipStages: string[];
  ageRanges: string[];
  traits: string[];
  interests: string[];
  occasions: string[];
  desiredFeelings: string[];
  memoryHooks: string[];
  tags: string[];
  customTags: string[];
  bestScenarios?: string | null;
  unsuitableScenarios?: string | null;
  purchaseOrBookingTip?: string | null;
  ritualTip?: string | null;
  pairingIdeas?: string | null;
  confidence: number;
  source: "deepseek" | "rule";
  productDetails: Partial<ProductDetailsInput>;
  activityDetails: Partial<ActivityDetailsInput>;
}
export async function listCustomFields(): Promise<CustomField[]> { return apiRequest<CustomField[]>("/api/custom-fields"); }
export async function createCustomField(payload: { machineKey: string; displayName: string; description?: string; valueType: string; cardinality: string }): Promise<CustomField> { return apiRequest<CustomField>("/api/custom-fields", { method: "POST", body: payload }); }
export async function suggestGift(canonicalName: string, giftTypeCode: GiftTypeCode, currentValues: Record<string, unknown> = {}) { return apiRequest<GiftAISuggestion>("/api/ai/suggest", { method: "POST", body: { canonicalName, giftTypeCode, currentValues } }); }
export async function deepSeekStatus() { return apiRequest<{ configured: boolean; model: string }>("/api/settings/deepseek"); }
export async function getServerStatus() { return apiRequest<ServerStatus>("/api/status"); }
export async function saveDeepSeekKey(apiKey: string) { return apiRequest<{ configured: boolean; model: string }>("/api/settings/deepseek", { method: "PUT", body: { apiKey } }); }
export function startTaobaoLogin() { return apiRequest<TaobaoLoginSession>("/api/taobao/login", { method: "POST" }); }
export function taobaoLoginStatus(sessionId: string) { return apiRequest<TaobaoLoginSession>(`/api/taobao/login/${sessionId}/status`); }
export function taobaoLoginAction(sessionId: string, body: { action: "click" | "type" | "press" | "drag" | "reload"; x?: number; y?: number; endX?: number; endY?: number; text?: string; key?: string; }) { return apiRequest<TaobaoLoginSession>(`/api/taobao/login/${sessionId}/action`, { method: "POST", body }); }
export function completeTaobaoLogin(sessionId: string) { return apiRequest<TaobaoLoginSession>(`/api/taobao/login/${sessionId}/complete`, { method: "POST" }); }
export function clearTaobaoLogin() { return apiRequest<{ cleared: boolean }>("/api/taobao/login", { method: "DELETE" }); }
export function taobaoLoginScreenshotUrl(sessionId: string, nonce: number) { return `/api/taobao/login/${sessionId}/screenshot?nonce=${nonce}`; }
export async function downloadBlob(path: string): Promise<Blob> { const response = await fetch(path, { credentials: "include" }); if (!response.ok) throw new Error("下载失败"); return response.blob(); }
export async function uploadFile(path: string, file: File): Promise<Record<string, unknown>> { const form = new FormData(); form.append("file", file); const response = await fetch(path, { method: "POST", body: form, credentials: "include" }); if (!response.ok) throw new Error("上传失败"); return response.json(); }
