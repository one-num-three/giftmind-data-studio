import { apiRequest } from "./client";

export type GiftTypeCode = "product" | "activity";

export interface ProductDetailsInput {
  productForm: "physical" | "digital" | "hybrid";
  genericProductName?: string | null;
  materials: string[];
  shippingRequired: boolean;
  digitalDeliveryMethod?: string | null;
  personalizationMethods?: string[];
}

export interface ActivityDetailsInput {
  activityMode: "online" | "offline" | "hybrid";
  activityCategory?: string | null;
  serviceRegions: string[];
  durationMinutesMin?: number | null;
  durationMinutesMax?: number | null;
  participantsMin?: number | null;
  participantsMax?: number | null;
  pricingUnit?: string | null;
  bookingRequired?: boolean;
}

export interface BundleComponentInput {
  componentGiftId: string;
  componentName?: string | null;
  quantity: number;
  required: boolean;
  displayOrder: number;
}

export interface CommonGiftPayload {
  canonicalName: string;
  aliases: string[];
  shortDescription?: string | null;
  isCustomizable?: boolean;
  isBundle: boolean;
  bundleComponents: BundleComponentInput[];
  recipientTypes: string[];
  interests: string[];
  occasions: string[];
  tags: string[];
  priceMin?: number | null;
  priceMax?: number | null;
  currency: string;
  whyTemplate?: string | null;
  sourceUrls: string[];
  sourceNotes?: string | null;
}

export type GiftPayload = CommonGiftPayload & (
  | { giftTypeCode: "product"; productDetails: ProductDetailsInput; activityDetails?: never }
  | { giftTypeCode: "activity"; activityDetails: ActivityDetailsInput; productDetails?: never }
);

export type GiftRead = GiftPayload & {
  id: string;
  schemaVersion: number;
  completenessScore: number | null;
};

export async function createGift(payload: GiftPayload): Promise<GiftRead> {
  return apiRequest<GiftRead>("/api/gifts", { method: "POST", body: payload });
}

export async function getGift(giftId: string): Promise<GiftRead> {
  return apiRequest<GiftRead>(`/api/gifts/${giftId}`);
}

export async function updateGift(giftId: string, payload: GiftPayload): Promise<GiftRead> {
  return apiRequest<GiftRead>(`/api/gifts/${giftId}`, { method: "PUT", body: payload });
}
