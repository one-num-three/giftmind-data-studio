import { describe, expect, it } from "vitest";

import type { GiftRead } from "../../api/gifts";
import { fromGiftRead, toGiftPayload } from "../workbench";

const existingProduct = {
  id: "gift-1", schemaVersion: 1, completenessScore: 80, giftTypeCode: "product",
  canonicalName: "可编辑礼物", aliases: ["别名"], shortDescription: "说明", subcategoryCode: "desk",
  isCustomizable: true, isBundle: false, bundleComponents: [], status: "published", emoji: "🎁",
  recipientTypes: ["friend"], relationshipStages: ["close"], ageRanges: ["adult"], traits: ["curious"],
  interests: ["reading"], occasions: ["birthday"], desiredFeelings: ["delight"], memoryHooks: ["book club"],
  tags: ["desk"], customTags: ["brass"], priceMin: 10, priceMax: 20, isFree: false, currency: "CNY",
  leadDaysMin: 1, leadDaysMax: 3, rushAvailable: true, tabooFlags: ["none"], allergyNotes: "无",
  safetyNotes: "小件", unsuitableGroups: ["toddlers"], whyTemplate: "适合爱阅读的人", bestScenarios: "生日",
  unsuitableScenarios: "正式商务", purchaseOrBookingTip: "提前购买", ritualTip: "附上手写卡",
  pairingIdeas: "搭配书籍", collectorNotes: "限量版", sourceNotes: "官方", sourceUrls: ["https://example.com/gift"],
  confidenceLevel: "high", verifiedAt: "2026-07-27T00:00:00Z",
  productDetails: {
    productForm: "digital", genericProductName: "电子书", materials: ["data"], colors: ["blue"], sizes: ["standard"],
    specifications: { pages: 100 }, variantNotes: "新版", weightGrams: null, packageDimensions: null, sizeClass: "small",
    isBulky: false, isFragile: false, isConsumable: false, shelfLifeDays: null, storageRequirements: null,
    personalizationMethods: ["题词"], personalizationRequirements: "提供名字", deviceOrPlatformCompatibility: ["Kindle"],
    digitalDeliveryMethod: "download", shippingRequired: false, shippingNotes: null, returnRiskNotes: "数字商品不可退", warrantyExpectation: null,
  },
} satisfies GiftRead;

const { productDetails: _productDetails, ...commonActivityFields } = existingProduct;
const existingActivity = {
  ...commonActivityFields,
  giftTypeCode: "activity",
  activityDetails: {
    activityMode: "hybrid", activityCategory: "workshop", serviceRegions: ["Shanghai"], durationMinutesMin: 60, durationMinutesMax: 90,
    participantsMin: 2, participantsMax: 8, pricingUnit: "per person", scheduleType: "weekly", bookingRequired: true,
    bookingLeadDaysMin: 2, bookingLeadDaysMax: 7, validityDays: 30, includedItems: ["materials"], excludedItems: ["transport"],
    equipmentRequirements: "none", ageRestrictions: "18+", heightRestrictions: null, healthRestrictions: null, accessibilityNotes: "elevator",
    weatherDependency: "rain backup", indoorOutdoor: "hybrid", cancellationExpectation: "48h", rescheduleExpectation: "allowed", refundExpectation: "partial",
  },
} satisfies GiftRead;

describe("workbench payload serialization", () => {
  it("round-trips every writable common and product field when editing a gift", () => {
    const payload = toGiftPayload(fromGiftRead(existingProduct));

    expect(payload).toEqual(expect.objectContaining({
      status: "published", emoji: "🎁", relationshipStages: ["close"], memoryHooks: ["book club"],
      verifiedAt: "2026-07-27T00:00:00Z", sourceUrls: ["https://example.com/gift"],
    }));
    expect(payload.productDetails).toEqual(existingProduct.productDetails);
  });

  it("round-trips every activity-specific field when editing an activity", () => {
    expect(toGiftPayload(fromGiftRead(existingActivity)).activityDetails).toEqual(existingActivity.activityDetails);
  });
});
