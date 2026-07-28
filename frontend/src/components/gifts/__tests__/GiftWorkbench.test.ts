import { createPinia, setActivePinia } from "pinia";
import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import GiftWorkbenchView from "../../../views/GiftWorkbenchView.vue";

const { apiRequest, ApiError } = vi.hoisted(() => ({
  apiRequest: vi.fn(),
  ApiError: class extends Error {
    constructor(message: string, public status: number, public detail?: unknown) { super(message); }
  },
}));

vi.mock("../../../api/client", () => ({
  apiRequest,
  ApiError,
}));

function mountWorkbench(giftId?: string) {
  return mount(GiftWorkbenchView, {
    props: giftId ? { giftId } : undefined,
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

    expect(wrapper.find('[data-image-input]').exists()).toBe(true);
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

  it("requires confirmation when a populated digital delivery method would be discarded", async () => {
    const wrapper = mountWorkbench();
    await flushPromises();
    await wrapper.get('[data-product-form]').setValue("digital");
    await flushPromises();
    await wrapper.get('[data-digital-delivery]').setValue("download");
    await wrapper.get('[data-type="activity"]').trigger("click");

    expect(wrapper.text()).toContain("商品专属信息不会用于活动记录");
  });

  it("requires confirmation for personalization, service region, and booking values", async () => {
    const product = mountWorkbench();
    await flushPromises();
    await product.get('[data-personalization-methods]').setValue("题词");
    await product.get('[data-type="activity"]').trigger("click");
    expect(product.text()).toContain("商品专属信息不会用于活动记录");
    await product.get('[data-action="confirm-type-switch"]').trigger("click");
    await product.get('[data-service-regions]').setValue("上海");
    await product.get('[data-booking-required]').setValue(true);
    await product.get('[data-type="product"]').trigger("click");
    expect(product.text()).toContain("活动专属信息不会用于商品记录");
  });

  it("locks the type selector while editing an existing gift", async () => {
    apiRequest.mockResolvedValueOnce({
      id: "gift-1", giftTypeCode: "product", canonicalName: "书签", aliases: [], shortDescription: null,
      recipientTypes: [], interests: [], occasions: [], tags: [], priceMin: null, priceMax: null, currency: "CNY",
      sourceUrls: [], isCustomizable: false, isBundle: false, bundleComponents: [],
      productDetails: { productForm: "physical", materials: [], shippingRequired: false },
    });
    const wrapper = mountWorkbench("gift-1");
    await flushPromises();

    expect(wrapper.get('[data-type="activity"]').attributes("disabled")).toBeDefined();
  });

  it("blocks all save actions with actionable client validation errors", async () => {
    const wrapper = mountWorkbench();
    await wrapper.get('[data-field="canonical-name"]').setValue("   ");
    await wrapper.get('[data-action="save-next"]').trigger("click");
    await flushPromises();

    expect(wrapper.get('[data-save-errors]').text()).toContain("标准名称不能为空");
    expect(apiRequest).not.toHaveBeenCalled();
  });

  it("requires a delivery method for digital products before saving", async () => {
    const wrapper = mountWorkbench();
    await wrapper.get('[data-field="canonical-name"]').setValue("电子礼品卡");
    await wrapper.get('[data-product-form]').setValue("digital");
    await wrapper.get('[data-action="save-next"]').trigger("click");
    await flushPromises();

    expect(wrapper.get('[data-save-errors]').text()).toContain("数字商品必须填写数字交付方式");
    expect(apiRequest).not.toHaveBeenCalled();
  });

  it("shows exact duplicate details returned by a save conflict", async () => {
    apiRequest.mockImplementation((path: string) => {
      if (path.startsWith("/api/gifts/duplicates")) return Promise.resolve({ matches: [] });
      return Promise.reject(new ApiError("请求未能完成。", 409, { matches: [{ canonical_name: "黄铜书签", exact: true, similarity: 1 }] }));
    });
    const wrapper = mountWorkbench();
    await flushPromises();
    await wrapper.get('[data-field="canonical-name"]').setValue("黄铜书签");
    await wrapper.get('[data-action="save-next"]').trigger("click");
    await flushPromises();

    expect(wrapper.get('[data-duplicate-feedback]').text()).toContain("黄铜书签");
  });

  it("shows a near-duplicate warning when saving and continuing a new gift", async () => {
    apiRequest.mockImplementation((path: string) => path.startsWith("/api/gifts/duplicates")
      ? Promise.resolve({ matches: [{ canonical_name: "黄铜书签", exact: false, similarity: 0.9 }] })
      : Promise.resolve({ id: "saved-gift", giftTypeCode: "product" }));
    const wrapper = mountWorkbench();
    await flushPromises();
    await wrapper.get('[data-field="canonical-name"]').setValue("黄铜书签新版");
    await wrapper.get("form").trigger("submit");
    await flushPromises();

    expect(wrapper.get('[data-duplicate-feedback]').text()).toContain("相近记录：黄铜书签");
  });

  it("clears duplicate feedback after saving and creating the next blank record", async () => {
    apiRequest.mockImplementation((path: string) => path.startsWith("/api/gifts/duplicates")
      ? Promise.resolve({ matches: [{ canonical_name: "黄铜书签", exact: false, similarity: 0.9 }] })
      : Promise.resolve({ id: "saved-gift", giftTypeCode: "product" }));
    const wrapper = mountWorkbench();
    await flushPromises();
    await wrapper.get('[data-field="canonical-name"]').setValue("黄铜书签新版");
    await wrapper.get('[data-action="save-next"]').trigger("click");
    await flushPromises();

    expect((wrapper.get('[data-field="canonical-name"]').element as HTMLInputElement).value).toBe("");
    expect(wrapper.find('[data-duplicate-feedback]').exists()).toBe(false);
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

  it("creates the gift before uploading queued images and only then starts the next record", async () => {
    const callOrder: string[] = [];
    apiRequest.mockImplementation((path: string, options?: { method?: string }) => {
      if (path.startsWith("/api/gifts/duplicates")) return Promise.resolve({ matches: [] });
      if (path === "/api/gifts" && options?.method === "POST") {
        callOrder.push("create-gift");
        return Promise.resolve({ id: "saved-gift", giftTypeCode: "product" });
      }
      return Promise.resolve({});
    });
    vi.stubGlobal("URL", {
      ...URL,
      createObjectURL: vi.fn(() => "blob:front.jpg"),
      revokeObjectURL: vi.fn(),
    });
    vi.stubGlobal("fetch", vi.fn(async (_path: string, options?: RequestInit) => {
      if (options?.method === "POST") callOrder.push("upload-image");
      return { ok: true, json: async () => options?.method === "POST" ? { id: "image-1" } : [] };
    }));
    const wrapper = mountWorkbench();
    await flushPromises();
    await wrapper.get('[data-field="canonical-name"]').setValue("黄铜书签");
    const input = wrapper.get('[data-image-input]').element as HTMLInputElement;
    Object.defineProperty(input, "files", { configurable: true, value: [new File(["image"], "front.jpg", { type: "image/jpeg" })] });
    await wrapper.get('[data-image-input]').trigger("change");
    await wrapper.get('[data-action="save-next"]').trigger("click");
    await flushPromises();

    expect(callOrder).toEqual(["create-gift", "upload-image"]);
    expect((wrapper.get('[data-field="canonical-name"]').element as HTMLInputElement).value).toBe("");
    expect(wrapper.findAll("[data-pending-image]")).toHaveLength(0);
    wrapper.unmount();
    vi.unstubAllGlobals();
  });

  it("retains the saved gift form and failed image for retry", async () => {
    apiRequest.mockImplementation((path: string) => path.startsWith("/api/gifts/duplicates")
      ? Promise.resolve({ matches: [] })
      : Promise.resolve({ id: "saved-gift", giftTypeCode: "product" }));
    vi.stubGlobal("URL", {
      ...URL,
      createObjectURL: vi.fn(() => "blob:front.jpg"),
      revokeObjectURL: vi.fn(),
    });
    vi.stubGlobal("fetch", vi.fn(async (_path: string, options?: RequestInit) => options?.method === "POST"
      ? { ok: false, json: async () => ({ detail: "存储暂不可用" }) }
      : { ok: true, json: async () => [] }));
    const wrapper = mountWorkbench();
    await flushPromises();
    await wrapper.get('[data-field="canonical-name"]').setValue("黄铜书签");
    const input = wrapper.get('[data-image-input]').element as HTMLInputElement;
    Object.defineProperty(input, "files", { configurable: true, value: [new File(["image"], "front.jpg", { type: "image/jpeg" })] });
    await wrapper.get('[data-image-input]').trigger("change");
    await wrapper.get('[data-action="save-next"]').trigger("click");
    await flushPromises();

    expect((wrapper.get('[data-field="canonical-name"]').element as HTMLInputElement).value).toBe("黄铜书签");
    expect(wrapper.findAll("[data-pending-image]")).toHaveLength(1);
    expect(wrapper.get("[data-save-errors]").text()).toContain("礼物已保存，但图片上传失败");
    wrapper.unmount();
    vi.unstubAllGlobals();
  });
});
