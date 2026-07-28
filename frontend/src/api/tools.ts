import { apiRequest } from "./client";
import type { ActivityDetailsInput, GiftTypeCode, ProductDetailsInput } from "./gifts";

export interface CustomField { id: string; machineKey: string; displayName: string; description?: string; valueType: string; state: string; }
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
export async function saveDeepSeekKey(apiKey: string) { return apiRequest<{ configured: boolean; model: string }>("/api/settings/deepseek", { method: "PUT", body: { apiKey } }); }
export async function downloadBlob(path: string): Promise<Blob> { const response = await fetch(path, { credentials: "include" }); if (!response.ok) throw new Error("下载失败"); return response.blob(); }
export async function uploadFile(path: string, file: File): Promise<Record<string, unknown>> { const form = new FormData(); form.append("file", file); const response = await fetch(path, { method: "POST", body: form, credentials: "include" }); if (!response.ok) throw new Error("上传失败"); return response.json(); }
