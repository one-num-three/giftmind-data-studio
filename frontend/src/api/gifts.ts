import { apiRequest } from "./client";

export type GiftTypeCode = "product" | "activity";

export interface ProductDetailsInput {
  productForm: "physical" | "digital" | "hybrid";
  genericProductName?: string | null; materials: string[]; colors: string[]; sizes: string[]; specifications?: Record<string, unknown> | unknown[] | null;
  variantNotes?: string | null; weightGrams?: number | null; packageDimensions?: string | null; sizeClass?: string | null;
  isBulky: boolean; isFragile: boolean; isConsumable: boolean; shelfLifeDays?: number | null; storageRequirements?: string | null;
  personalizationMethods: string[]; personalizationRequirements?: string | null; deviceOrPlatformCompatibility: string[];
  digitalDeliveryMethod?: string | null; shippingRequired: boolean; shippingNotes?: string | null; returnRiskNotes?: string | null; warrantyExpectation?: string | null;
}

export interface ActivityDetailsInput {
  activityMode: "online" | "offline" | "hybrid"; activityCategory?: string | null; serviceRegions: string[];
  durationMinutesMin?: number | null; durationMinutesMax?: number | null; participantsMin?: number | null; participantsMax?: number | null;
  pricingUnit?: string | null; scheduleType?: string | null; bookingRequired: boolean; bookingLeadDaysMin?: number | null; bookingLeadDaysMax?: number | null;
  validityDays?: number | null; includedItems: string[]; excludedItems: string[]; equipmentRequirements?: string | null;
  ageRestrictions?: string | null; heightRestrictions?: string | null; healthRestrictions?: string | null; accessibilityNotes?: string | null;
  weatherDependency?: string | null; indoorOutdoor?: string | null; cancellationExpectation?: string | null; rescheduleExpectation?: string | null; refundExpectation?: string | null;
}

export interface BundleComponentInput {
  componentGiftId: string; componentTypeCode?: string | null; componentName?: string | null; quantity: number; required: boolean; displayOrder: number; roleNotes?: string | null;
}

export interface CommonGiftPayload {
  canonicalName: string; aliases: string[]; shortDescription?: string | null; subcategoryCode?: string | null;
  isCustomizable: boolean; isBundle: boolean; bundleComponents: BundleComponentInput[]; status: string; emoji?: string | null;
  recipientTypes: string[]; relationshipStages: string[]; ageRanges: string[]; traits: string[]; interests: string[]; occasions: string[];
  desiredFeelings: string[]; memoryHooks: string[]; tags: string[]; customTags: string[];
  priceMin?: number | null; priceMax?: number | null; isFree: boolean; currency: string; leadDaysMin?: number | null; leadDaysMax?: number | null; rushAvailable: boolean;
  tabooFlags: string[]; allergyNotes?: string | null; safetyNotes?: string | null; unsuitableGroups: string[];
  whyTemplate?: string | null; bestScenarios?: string | null; unsuitableScenarios?: string | null; purchaseOrBookingTip?: string | null;
  ritualTip?: string | null; pairingIdeas?: string | null; collectorNotes?: string | null; sourceUrls: string[]; sourceNotes?: string | null;
  confidenceLevel?: string | null; verifiedAt?: string | null;
}

export type GiftPayload = CommonGiftPayload & (
  | { giftTypeCode: "product"; productDetails: ProductDetailsInput; activityDetails?: never }
  | { giftTypeCode: "activity"; activityDetails: ActivityDetailsInput; productDetails?: never }
);

export type GiftRead = GiftPayload & { id: string; schemaVersion: number; completenessScore: number | null; createdAt?: string; updatedAt?: string; deletedAt?: string | null };
export interface DuplicateMatch { canonical_name: string; similarity: number; exact: boolean; }
export interface GiftListFilters {
  q?: string; status?: string; giftType?: GiftTypeCode; carrierOrMode?: string; isCustomizable?: boolean;
  isBundle?: boolean; priceMin?: number; priceMax?: number; minCompleteness?: number; hasImage?: boolean;
  hasOffer?: boolean; verified?: boolean; deleted?: "exclude" | "only"; page?: number; pageSize?: number;
}
export interface GiftListResponse { items: GiftRead[]; total: number; page: number; pageSize: number; }
export interface AuditEventRead { eventType: string; entityType: string; entityId: string | null; payloadJson: Record<string, unknown> | unknown[] | null; createdAt: string; }
export interface DashboardSummary {
  total: number; complete: number; drafts: number; needsReview: number; inactive: number; productCount: number;
  activityCount: number; missingImages: number; missingSources: number; staleChannels: number; possibleDuplicates: number;
  recentChanges: AuditEventRead[];
}

export async function createGift(payload: GiftPayload): Promise<GiftRead> { return apiRequest<GiftRead>("/api/gifts", { method: "POST", body: payload }); }
export async function getGift(giftId: string): Promise<GiftRead> { return apiRequest<GiftRead>(`/api/gifts/${giftId}`); }
export async function updateGift(giftId: string, payload: GiftPayload): Promise<GiftRead> { return apiRequest<GiftRead>(`/api/gifts/${giftId}`, { method: "PUT", body: payload }); }
export async function listGifts(filters: GiftListFilters = {}): Promise<GiftListResponse> {
  const search = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== "") search.set(key, String(value));
  });
  const suffix = search.size ? `?${search}` : "";
  return apiRequest<GiftListResponse>(`/api/gifts${suffix}`);
}
export async function getDashboard(): Promise<DashboardSummary> { return apiRequest<DashboardSummary>("/api/dashboard"); }
export async function copyGift(giftId: string): Promise<GiftRead> { return apiRequest<GiftRead>(`/api/gifts/${giftId}/copy`, { method: "POST" }); }
export async function deleteGift(giftId: string): Promise<void> { return apiRequest<void>(`/api/gifts/${giftId}`, { method: "DELETE" }); }
export async function restoreGift(giftId: string): Promise<GiftRead> { return apiRequest<GiftRead>(`/api/recycle-bin/gifts/${giftId}/restore`, { method: "POST" }); }
export async function purgeGift(giftId: string, canonicalName: string): Promise<void> { return apiRequest<void>(`/api/recycle-bin/gifts/${giftId}`, { method: "DELETE", body: { canonicalName } }); }
export async function updateGiftStatus(giftIds: string[], status: string): Promise<{ affected: number }> {
  return apiRequest<{ affected: number }>("/api/gifts/bulk/status", { method: "PATCH", body: { giftIds, status } });
}
export async function findGiftDuplicates(canonicalName: string, aliases: string[]): Promise<DuplicateMatch[]> {
  const search = new URLSearchParams({ canonicalName });
  aliases.forEach((alias) => search.append("aliases", alias));
  const result = await apiRequest<{ matches: DuplicateMatch[] }>(`/api/gifts/duplicates?${search}`);
  return Array.isArray(result.matches) ? result.matches : [];
}
