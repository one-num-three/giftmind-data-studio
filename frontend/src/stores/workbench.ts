import { defineStore } from "pinia";

import { createGift, getGift, updateGift } from "../api/gifts";
import type { ActivityDetailsInput, BundleComponentInput, CommonGiftPayload, GiftPayload, GiftRead, ProductDetailsInput } from "../api/gifts";

export interface CommonGiftDraft extends Omit<CommonGiftPayload, "sourceUrls"> { channels: string[]; }
export type ProductGiftDraft = CommonGiftDraft & { giftTypeCode: "product"; productDetails: ProductDetailsInput; activityDetails?: never; };
export type ActivityGiftDraft = CommonGiftDraft & { giftTypeCode: "activity"; activityDetails: ActivityDetailsInput; productDetails?: never; };
export type GiftDraft = ProductGiftDraft | ActivityGiftDraft;
export interface WorkbenchState { giftId: string | null; draftId: string; draft: GiftDraft; saving: boolean; dirty: boolean; savedGift: GiftRead | null; }
const ACTIVE_DRAFT_ID_KEY = "giftmind.workbench.activeDraftId";
function createDraftId(): string {
  const id = crypto.randomUUID();
  localStorage.setItem(ACTIVE_DRAFT_ID_KEY, id);
  return id;
}
function initialDraftId(): string {
  const stored = localStorage.getItem(ACTIVE_DRAFT_ID_KEY);
  return stored && /^[0-9a-f-]{36}$/i.test(stored) ? stored : createDraftId();
}

function createCommonDraft(): CommonGiftDraft {
  return {
    canonicalName: "", aliases: [], shortDescription: "", subcategoryCode: null, isCustomizable: false, isBundle: false, bundleComponents: [], status: "draft", emoji: null,
    recipientTypes: [], relationshipStages: [], ageRanges: [], traits: [], interests: [], occasions: [], desiredFeelings: [], memoryHooks: [], tags: [], customTags: [],
    priceMin: null, priceMax: null, isFree: false, currency: "CNY", leadDaysMin: null, leadDaysMax: null, rushAvailable: false,
    tabooFlags: [], allergyNotes: null, safetyNotes: null, unsuitableGroups: [], whyTemplate: "", bestScenarios: null, unsuitableScenarios: null,
    purchaseOrBookingTip: null, ritualTip: null, pairingIdeas: null, collectorNotes: null, channels: [], sourceNotes: "", confidenceLevel: null, verifiedAt: null,
  };
}

export function createProductDetails(): ProductDetailsInput {
  return {
    productForm: "physical", genericProductName: null, materials: [], colors: [], sizes: [], specifications: null, variantNotes: null, weightGrams: null,
    packageDimensions: null, sizeClass: null, isBulky: false, isFragile: false, isConsumable: false, shelfLifeDays: null, storageRequirements: null,
    personalizationMethods: [], personalizationRequirements: null, deviceOrPlatformCompatibility: [], digitalDeliveryMethod: null, shippingRequired: false,
    shippingNotes: null, returnRiskNotes: null, warrantyExpectation: null,
  };
}

export function createActivityDetails(): ActivityDetailsInput {
  return {
    activityMode: "offline", activityCategory: null, serviceRegions: [], durationMinutesMin: null, durationMinutesMax: null, participantsMin: null,
    participantsMax: null, pricingUnit: null, scheduleType: null, bookingRequired: false, bookingLeadDaysMin: null, bookingLeadDaysMax: null,
    validityDays: null, includedItems: [], excludedItems: [], equipmentRequirements: null, ageRestrictions: null, heightRestrictions: null,
    healthRestrictions: null, accessibilityNotes: null, weatherDependency: null, indoorOutdoor: null, cancellationExpectation: null,
    rescheduleExpectation: null, refundExpectation: null,
  };
}

export function createProductDraft(): ProductGiftDraft { return { ...createCommonDraft(), giftTypeCode: "product", productDetails: createProductDetails() }; }
export function createActivityDraft(): ActivityGiftDraft { return { ...createCommonDraft(), giftTypeCode: "activity", activityDetails: createActivityDetails() }; }

export function toGiftPayload(draft: GiftDraft): GiftPayload {
  const { channels, giftTypeCode, productDetails, activityDetails, ...common } = draft;
  return giftTypeCode === "product"
    ? { ...common, sourceUrls: channels.filter(Boolean), giftTypeCode, productDetails: productDetails! }
    : { ...common, sourceUrls: channels.filter(Boolean), giftTypeCode, activityDetails: activityDetails! };
}

export function fromGiftRead(gift: GiftRead): GiftDraft {
  const { id: _id, schemaVersion: _schemaVersion, completenessScore: _completenessScore, giftTypeCode, productDetails, activityDetails, sourceUrls, ...common } = gift;
  return giftTypeCode === "product"
    ? { ...createCommonDraft(), ...common, channels: sourceUrls ?? [], giftTypeCode, productDetails: { ...createProductDetails(), ...productDetails } }
    : { ...createCommonDraft(), ...common, channels: sourceUrls ?? [], giftTypeCode, activityDetails: { ...createActivityDetails(), ...activityDetails } };
}

function rangeErrors(minimum: number | null | undefined, maximum: number | null | undefined, label: string): string[] {
  if ((minimum !== null && minimum !== undefined && (!Number.isFinite(minimum) || minimum < 0)) || (maximum !== null && maximum !== undefined && (!Number.isFinite(maximum) || maximum < 0))) return [`${label}必须是非负数字`];
  return minimum !== null && minimum !== undefined && maximum !== null && maximum !== undefined && minimum > maximum ? [`${label}起始值不能大于结束值`] : [];
}

export function validateGiftDraft(draft: GiftDraft): string[] {
  const errors: string[] = [];
  if (!draft.canonicalName.trim()) errors.push("标准名称不能为空");
  errors.push(...rangeErrors(draft.priceMin, draft.priceMax, "价格范围"), ...rangeErrors(draft.leadDaysMin, draft.leadDaysMax, "准备天数"));
  if (draft.isFree && (draft.priceMin !== null || draft.priceMax !== null)) errors.push("免费礼物不能填写价格");
  if (!draft.isFree && draft.priceMin === 0 && draft.priceMax === 0) errors.push("零元礼物请标记为免费");
  if (draft.isBundle !== Boolean(draft.bundleComponents.length)) errors.push("组合礼物必须且只能填写组合组件");
  if (draft.giftTypeCode === "product") {
    const details = draft.productDetails;
    if (details.productForm === "digital" && details.shippingRequired) errors.push("数字商品不能要求配送");
    if (details.productForm === "digital" && !details.digitalDeliveryMethod?.trim()) errors.push("数字商品必须填写数字交付方式");
    if (details.productForm === "physical" && details.digitalDeliveryMethod?.trim()) errors.push("实物商品不能填写数字交付方式");
    if (draft.isCustomizable && !details.personalizationMethods.length) errors.push("可定制商品必须填写个性化方式");
  } else {
    const details = draft.activityDetails;
    errors.push(...rangeErrors(details.durationMinutesMin, details.durationMinutesMax, "活动时长"), ...rangeErrors(details.participantsMin, details.participantsMax, "参与人数"), ...rangeErrors(details.bookingLeadDaysMin, details.bookingLeadDaysMax, "预约提前天数"));
    if (details.activityMode === "online" && details.weatherDependency?.trim()) errors.push("线上活动不能填写天气依赖");
  }
  return errors;
}

export const useWorkbenchStore = defineStore("workbench", {
  state: (): WorkbenchState => ({ giftId: null, draftId: initialDraftId(), draft: createProductDraft(), saving: false, dirty: false, savedGift: null }),
  actions: {
    startNew() { this.giftId = null; this.draftId = createDraftId(); this.draft = createProductDraft(); this.savedGift = null; this.dirty = false; },
    replaceDraft(draft: GiftDraft) { this.draft = draft; this.dirty = true; }, markDirty() { this.dirty = true; },
    async load(giftId: string) { this.saving = true; try { const gift = await getGift(giftId); this.giftId = gift.id; this.draftId = gift.id; this.savedGift = gift; this.draft = fromGiftRead(gift); this.dirty = false; } finally { this.saving = false; } },
    async saveDraft(): Promise<GiftRead> { this.saving = true; try { const saved = this.giftId ? await updateGift(this.giftId, toGiftPayload(this.draft)) : await createGift(toGiftPayload(this.draft)); this.giftId = saved.id; this.savedGift = saved; this.dirty = false; return saved; } finally { this.saving = false; } },
    async saveAndContinue(): Promise<GiftRead> { return this.saveDraft(); }, async saveAndCreateNext(): Promise<void> { await this.saveDraft(); this.startNew(); },
  },
});
