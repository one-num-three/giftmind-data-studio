import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import CommonFieldsSection from "../CommonFieldsSection.vue";
import { createProductDraft } from "../../../stores/workbench";

const { suggestGift } = vi.hoisted(() => ({ suggestGift: vi.fn() }));

vi.mock("../../../api/tools", () => ({ suggestGift }));

describe("CommonFieldsSection AI prefill", () => {
  it("fills common fields and matching choices from a complete suggestion", async () => {
    suggestGift.mockResolvedValue({
      recommendedGiftTypeCode: "product",
      subcategoryCode: "stationery",
      shortDescription: "南京博物院主题金属书签。",
      whyTemplate: "适合送给喜欢阅读和南京文化的朋友。",
      priceMin: 39,
      priceMax: 99,
      recipientTypes: ["朋友"],
      occasions: ["生日"],
      interests: ["阅读", "旅行"],
      tags: ["有仪式感", "小众"],
      source: "deepseek",
      productDetails: { genericProductName: "金属书签", materials: ["金属"], personalizationMethods: [], shippingRequired: true },
    });
    const draft = createProductDraft();
    draft.canonicalName = "南京博物院文创书签";

    const wrapper = mount(CommonFieldsSection, { props: { modelValue: draft } });
    expect(wrapper.get('[data-ai-review]').attributes("open")).toBeUndefined();
    await wrapper.get("button.ai-button").trigger("click");

    expect(wrapper.get('[data-ai-review]').attributes("open")).toBeDefined();
    expect(draft.shortDescription).toBe("南京博物院主题金属书签。");
    expect(draft.whyTemplate).toContain("适合送给");
    expect(draft.priceMin).toBe(39);
    expect(draft.priceMax).toBe(99);
    expect(draft.recipientTypes).toEqual(["朋友"]);
    expect(draft.occasions).toEqual(["生日"]);
    expect(draft.interests).toEqual(["阅读", "旅行"]);
    expect(draft.tags).toEqual(["有仪式感", "小众"]);
  });
});
