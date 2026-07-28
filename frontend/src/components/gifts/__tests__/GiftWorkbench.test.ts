import { createPinia, setActivePinia } from "pinia";
import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import GiftWorkbenchView from "../../../views/GiftWorkbenchView.vue";

const { apiRequest } = vi.hoisted(() => ({ apiRequest: vi.fn() }));

vi.mock("../../../api/client", () => ({
  apiRequest,
}));

function mountWorkbench() {
  return mount(GiftWorkbenchView, {
    global: { plugins: [createPinia()] },
  });
}

describe("GiftWorkbenchView", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    apiRequest.mockReset();
    localStorage.clear();
  });

  it("shows only product fields after product confirmation", async () => {
    const wrapper = mountWorkbench();

    await wrapper.get('[data-type="product"]').trigger("click");

    expect(wrapper.find('[data-section="product"]').exists()).toBe(true);
    expect(wrapper.find('[data-section="activity"]').exists()).toBe(false);
  });

  it("requires confirmation before discarding type-specific values", async () => {
    const wrapper = mountWorkbench();
    await wrapper.get('[data-type="product"]').trigger("click");
    await wrapper.get('[data-product-materials]').setValue("黄铜");
    await wrapper.get('[data-type="activity"]').trigger("click");

    expect(wrapper.text()).toContain("商品专属信息不会用于活动记录");
  });

  it("restores a matching local draft only after the user chooses restore", async () => {
    localStorage.setItem("giftmind.workbench.v1.new", JSON.stringify({
      version: 1,
      draft: {
        giftTypeCode: "product",
        canonicalName: "本地书签",
        aliases: [],
        shortDescription: "",
        recipientTypes: [],
        occasions: [],
        interests: [],
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
      },
    }));

    const wrapper = mountWorkbench();
    expect(wrapper.text()).toContain("发现未完成的本地草稿");
    await wrapper.get('[data-action="restore-draft"]').trigger("click");

    expect((wrapper.get('[data-field="canonical-name"]').element as HTMLInputElement).value).toBe("本地书签");
  });

  it("saves the draft and starts a new record when requested", async () => {
    apiRequest.mockResolvedValue({ id: "saved-gift", giftTypeCode: "product" });
    const wrapper = mountWorkbench();
    await wrapper.get('[data-type="product"]').trigger("click");
    await wrapper.get('[data-field="canonical-name"]').setValue("黄铜书签");
    await wrapper.get('[data-action="save-next"]').trigger("click");
    await flushPromises();

    expect(apiRequest).toHaveBeenCalledWith("/api/gifts", expect.objectContaining({ method: "POST" }));
    expect((wrapper.get('[data-field="canonical-name"]').element as HTMLInputElement).value).toBe("");
  });
});
