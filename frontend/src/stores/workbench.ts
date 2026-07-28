import { defineStore } from "pinia";

import { createGift, getGift, updateGift } from "../api/gifts";
import type { ActivityDetailsInput, BundleComponentInput, GiftPayload, GiftRead, ProductDetailsInput } from "../api/gifts";

export interface CommonGiftDraft {
  canonicalName: string;
  aliases: string[];
  shortDescription: string;
  recipientTypes: string[];
  interests: string[];
  occasions: string[];
  tags: string[];
  priceMin: number | null;
  priceMax: number | null;
  currency: string;
  whyTemplate: string;
  channels: string[];
  sourceNotes: string;
  isCustomizable: boolean;
  isBundle: boolean;
  bundleComponents: BundleComponentInput[];
}

export type ProductGiftDraft = CommonGiftDraft & {
  giftTypeCode: "product";
  productDetails: ProductDetailsInput;
  activityDetails?: never;
};

export type ActivityGiftDraft = CommonGiftDraft & {
  giftTypeCode: "activity";
  activityDetails: ActivityDetailsInput;
  productDetails?: never;
};

export type GiftDraft = ProductGiftDraft | ActivityGiftDraft;

export interface WorkbenchState {
  giftId: string | null;
  draft: GiftDraft;
  saving: boolean;
  dirty: boolean;
  savedGift: GiftRead | null;
}

export function createProductDraft(): ProductGiftDraft {
  return {
    giftTypeCode: "product",
    canonicalName: "",
    aliases: [],
    shortDescription: "",
    recipientTypes: [],
    interests: [],
    occasions: [],
    tags: [],
    priceMin: null,
    priceMax: null,
    currency: "CNY",
    whyTemplate: "",
    channels: [],
    sourceNotes: "",
    isCustomizable: false,
    isBundle: false,
    bundleComponents: [],
    productDetails: { productForm: "physical", materials: [], shippingRequired: false },
  };
}

export function createActivityDraft(): ActivityGiftDraft {
  const common = createProductDraft();
  const { productDetails: _productDetails, ...withoutProduct } = common;
  return {
    ...withoutProduct,
    giftTypeCode: "activity",
    activityDetails: { activityMode: "offline", serviceRegions: [] },
  };
}

export function toGiftPayload(draft: GiftDraft): GiftPayload {
  const common = {
    canonicalName: draft.canonicalName.trim(),
    aliases: draft.aliases,
    shortDescription: draft.shortDescription || null,
    recipientTypes: draft.recipientTypes,
    interests: draft.interests,
    occasions: draft.occasions,
    tags: draft.tags,
    priceMin: draft.priceMin,
    priceMax: draft.priceMax,
    currency: draft.currency,
    whyTemplate: draft.whyTemplate || null,
    sourceUrls: draft.channels.filter(Boolean),
    sourceNotes: draft.sourceNotes || null,
    isCustomizable: draft.isCustomizable,
    isBundle: draft.isBundle,
    bundleComponents: draft.bundleComponents,
  };
  return draft.giftTypeCode === "product"
    ? { ...common, giftTypeCode: "product", productDetails: draft.productDetails }
    : { ...common, giftTypeCode: "activity", activityDetails: draft.activityDetails };
}

function fromGiftRead(gift: GiftRead): GiftDraft {
  const common: CommonGiftDraft = {
    canonicalName: gift.canonicalName,
    aliases: gift.aliases ?? [],
    shortDescription: gift.shortDescription ?? "",
    recipientTypes: gift.recipientTypes ?? [],
    interests: gift.interests ?? [],
    occasions: gift.occasions ?? [],
    tags: gift.tags ?? [],
    priceMin: gift.priceMin ?? null,
    priceMax: gift.priceMax ?? null,
    currency: gift.currency ?? "CNY",
    whyTemplate: gift.whyTemplate ?? "",
    channels: gift.sourceUrls ?? [],
    sourceNotes: gift.sourceNotes ?? "",
    isCustomizable: gift.isCustomizable ?? false,
    isBundle: gift.isBundle ?? false,
    bundleComponents: gift.bundleComponents ?? [],
  };
  return gift.giftTypeCode === "product"
    ? { ...common, giftTypeCode: "product", productDetails: gift.productDetails }
    : { ...common, giftTypeCode: "activity", activityDetails: gift.activityDetails };
}

export const useWorkbenchStore = defineStore("workbench", {
  state: (): WorkbenchState => ({
    giftId: null,
    draft: createProductDraft(),
    saving: false,
    dirty: false,
    savedGift: null,
  }),
  actions: {
    startNew() {
      this.giftId = null;
      this.draft = createProductDraft();
      this.savedGift = null;
      this.dirty = false;
    },
    replaceDraft(draft: GiftDraft) {
      this.draft = draft;
      this.dirty = true;
    },
    markDirty() {
      this.dirty = true;
    },
    async load(giftId: string) {
      this.saving = true;
      try {
        const gift = await getGift(giftId);
        this.giftId = gift.id;
        this.savedGift = gift;
        this.draft = fromGiftRead(gift);
        this.dirty = false;
      } finally {
        this.saving = false;
      }
    },
    async saveDraft(): Promise<GiftRead> {
      this.saving = true;
      try {
        const saved = this.giftId
          ? await updateGift(this.giftId, toGiftPayload(this.draft))
          : await createGift(toGiftPayload(this.draft));
        this.giftId = saved.id;
        this.savedGift = saved;
        this.dirty = false;
        return saved;
      } finally {
        this.saving = false;
      }
    },
    async saveAndContinue(): Promise<GiftRead> {
      return this.saveDraft();
    },
    async saveAndCreateNext(): Promise<void> {
      await this.saveDraft();
      this.startNew();
    },
  },
});
