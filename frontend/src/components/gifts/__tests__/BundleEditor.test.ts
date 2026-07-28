import { flushPromises, mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import BundleEditor from "../BundleEditor.vue";

const { apiRequest } = vi.hoisted(() => ({ apiRequest: vi.fn() }));

vi.mock("../../../api/client", () => ({ apiRequest }));

function gift(id: string, canonicalName: string) {
  return { id, giftTypeCode: "product", canonicalName, isBundle: false, bundleComponents: [] };
}

describe("BundleEditor", () => {
  it("loads every active page and excludes the gift being edited", async () => {
    apiRequest.mockImplementation((path: string) => Promise.resolve(path.includes("page=2")
      ? { items: [gift("later", "第二页礼物")], total: 101, page: 2, pageSize: 100 }
      : { items: [gift("current", "当前组合"), gift("first", "首页礼物")], total: 101, page: 1, pageSize: 100 }));
    const wrapper = mount(BundleEditor, {
      props: {
        currentGiftId: "current",
        modelValue: { isBundle: false, bundleComponents: [] } as never,
      },
    });

    await wrapper.get('input[type="checkbox"]').setValue(true);
    await flushPromises();

    expect(apiRequest).toHaveBeenCalledWith(expect.stringContaining("page=2"));
    expect(wrapper.text()).toContain("首页礼物");
    expect(wrapper.text()).toContain("第二页礼物");
    expect(wrapper.text()).not.toContain("当前组合");
  });
});
