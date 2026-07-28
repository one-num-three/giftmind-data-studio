import { flushPromises, mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import ToolsView from "../ToolsView.vue";

const { apiRequest } = vi.hoisted(() => ({ apiRequest: vi.fn() }));
const { push } = vi.hoisted(() => ({ push: vi.fn() }));

vi.mock("../../api/client", () => ({ apiRequest }));
vi.mock("vue-router", () => ({ useRouter: () => ({ push }) }));

describe("tools view DeepSeek settings", () => {
  it("shows configuration status and saves the key without keeping it in the input", async () => {
    apiRequest.mockImplementation((path: string) => {
      if (path === "/api/custom-fields") return Promise.resolve([]);
      if (path === "/api/settings/deepseek") return Promise.resolve({ configured: false, model: "deepseek-v4-flash" });
      return Promise.resolve({ configured: true, model: "deepseek-v4-flash" });
    });

    const wrapper = mount(ToolsView);
    await flushPromises();

    const input = wrapper.get('[data-field="deepseek-key"]');
    expect(input.attributes("type")).toBe("password");
    expect(wrapper.text()).toContain("尚未配置 · DeepSeek V4 Flash");

    await input.setValue("sk-preview-secret-12345");
    await wrapper.get('[data-action="save-deepseek-key"]').trigger("click");
    await flushPromises();

    expect(apiRequest).toHaveBeenCalledWith("/api/settings/deepseek", {
      method: "PUT",
      body: { apiKey: "sk-preview-secret-12345" },
    });
    expect((input.element as HTMLInputElement).value).toBe("");
    expect(wrapper.text()).toContain("已配置 · DeepSeek V4 Flash");
  });

  it("still checks the key status when the custom-field list is unavailable", async () => {
    apiRequest.mockImplementation((path: string) => {
      if (path === "/api/custom-fields") return Promise.reject(new Error("field service unavailable"));
      return Promise.resolve({ configured: false, model: "deepseek-v4-flash" });
    });

    const wrapper = mount(ToolsView);
    await flushPromises();

    expect(wrapper.text()).toContain("尚未配置 · DeepSeek V4 Flash");
  });

  it("analyzes multiple links, shows duplicate warnings, and hands one item to the workbench", async () => {
    apiRequest.mockImplementation((path: string) => {
      if (path === "/api/custom-fields") return Promise.resolve([]);
      if (path === "/api/settings/deepseek") return Promise.resolve({ configured: true, model: "deepseek-v4-flash" });
      if (path === "/api/ai/batch-links") return Promise.resolve({
        items: [{
          url: "https://example.com/gift",
          suggestedName: "黄铜书签",
          status: "ok",
          patches: [{ path: "canonicalName", label: "标准名称", value: "黄铜书签", confidence: .9, status: "pending" }],
          duplicates: [{ canonical_name: "黄铜书签", exact: true, similarity: 1 }],
        }],
      });
      return Promise.resolve({});
    });
    const wrapper = mount(ToolsView);
    await flushPromises();
    await wrapper.get("[data-batch-links]").setValue("https://example.com/gift");
    await wrapper.get("[data-analyze-links]").trigger("click");
    await flushPromises();

    expect(apiRequest).toHaveBeenCalledWith("/api/ai/batch-links", {
      method: "POST",
      body: { urls: ["https://example.com/gift"], giftTypeCode: "product" },
    });
    expect(wrapper.text()).toContain("发现完全重复");
    await wrapper.get("[data-review-batch-item]").trigger("click");
    expect(sessionStorage.getItem("giftmind.batchDraft")).toContain("黄铜书签");
    expect(push).toHaveBeenCalledWith({ name: "gift-create" });
  });
});
