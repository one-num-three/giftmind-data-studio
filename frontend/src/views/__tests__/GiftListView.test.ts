import { flushPromises, mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import GiftListView from "../GiftListView.vue";
import RecycleBinView from "../RecycleBinView.vue";

const { apiRequest } = vi.hoisted(() => ({ apiRequest: vi.fn() }));

vi.mock("../../api/client", () => ({ apiRequest }));

const gifts = [
  { id: "product-1", giftTypeCode: "product", canonicalName: "黄铜书签", status: "active", completenessScore: 100, isBundle: false, bundleComponents: [] },
  { id: "activity-1", giftTypeCode: "activity", canonicalName: "陶艺体验", status: "draft", completenessScore: 40, isBundle: false, bundleComponents: [] },
];

function createTestRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/gifts", name: "gift-list", component: GiftListView },
      { path: "/gifts/new", name: "gift-create", component: { template: "<div />" } },
      { path: "/gifts/:giftId", name: "gift-edit", component: { template: "<div />" } },
      { path: "/recycle-bin", name: "recycle-bin", component: RecycleBinView },
    ],
  });
}

describe("gift discovery and recycle-bin views", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    apiRequest.mockReset();
    apiRequest.mockImplementation((path: string) => {
      if (path.startsWith("/api/recycle-bin/gifts")) return Promise.resolve({ items: [gifts[0]], total: 1, page: 1, pageSize: 50 });
      if (path.startsWith("/api/gifts")) return Promise.resolve({ items: gifts, total: gifts.length, page: 1, pageSize: 50 });
      return Promise.resolve(undefined);
    });
  });

  afterEach(() => vi.useRealTimers());

  it("debounces URL-backed search, filters by type, toggles cards, and confirms copies", async () => {
    const router = createTestRouter();
    await router.push("/gifts");
    await router.isReady();
    const wrapper = mount(GiftListView, { global: { plugins: [router] } });
    await flushPromises();

    await wrapper.get('[data-filter="gift-type"]').setValue("activity");
    await wrapper.get('[data-filter="search"]').setValue("陶艺");
    await vi.advanceTimersByTimeAsync(300);
    await flushPromises();

    expect(router.currentRoute.value.query).toMatchObject({ giftType: "activity", q: "陶艺" });
    expect(apiRequest).toHaveBeenLastCalledWith(expect.stringContaining("giftType=activity"));
    expect(apiRequest).toHaveBeenLastCalledWith(expect.stringContaining("q=%E9%99%B6%E8%89%BA"));
    await wrapper.get('[data-action="cards"]').trigger("click");
    await flushPromises();
    expect(wrapper.find('[data-view="cards"]').exists()).toBe(true);
    expect(router.currentRoute.value.query.view).toBe("cards");
    await wrapper.get('[data-action="copy-product-1"]').trigger("click");
    expect(wrapper.get('[data-copy-confirm]').text()).toContain("黄铜书签");
    await wrapper.get('[data-action="confirm-copy"]').trigger("click");
    await flushPromises();
    expect(apiRequest).toHaveBeenCalledWith("/api/gifts/product-1/copy", { method: "POST" });
  });

  it("restores a recycled gift through the recycle API", async () => {
    const router = createTestRouter();
    await router.push("/recycle-bin");
    await router.isReady();
    const wrapper = mount(RecycleBinView, { global: { plugins: [router] } });
    await flushPromises();

    await wrapper.get('[data-action="restore-product-1"]').trigger("click");
    await flushPromises();

    expect(apiRequest).toHaveBeenCalledWith("/api/recycle-bin/gifts/product-1/restore", { method: "POST" });
  });

  it("moves through every gift-list page without dropping active filters", async () => {
    apiRequest.mockImplementation((path: string) => Promise.resolve(path.includes("page=2")
      ? { items: [gifts[1]], total: 101, page: 2, pageSize: 50 }
      : { items: [gifts[0]], total: 101, page: 1, pageSize: 50 }));
    const router = createTestRouter();
    await router.push("/gifts?giftType=product");
    await router.isReady();
    const wrapper = mount(GiftListView, { global: { plugins: [router] } });
    await flushPromises();

    await wrapper.get('[data-action="next-page"]').trigger("click");
    await flushPromises();

    expect(apiRequest).toHaveBeenLastCalledWith(expect.stringContaining("giftType=product"));
    expect(apiRequest).toHaveBeenLastCalledWith(expect.stringContaining("page=2"));
    expect(wrapper.text()).toContain("陶艺体验");
  });

  it("moves through every recycle-bin page", async () => {
    apiRequest.mockImplementation((path: string) => Promise.resolve(path.includes("page=2")
      ? { items: [gifts[1]], total: 51, page: 2, pageSize: 50 }
      : { items: [gifts[0]], total: 51, page: 1, pageSize: 50 }));
    const router = createTestRouter();
    await router.push("/recycle-bin");
    await router.isReady();
    const wrapper = mount(RecycleBinView, { global: { plugins: [router] } });
    await flushPromises();

    await wrapper.get('[data-action="next-page"]').trigger("click");
    await flushPromises();

    expect(apiRequest).toHaveBeenLastCalledWith(expect.stringContaining("deleted=only"));
    expect(apiRequest).toHaveBeenLastCalledWith(expect.stringContaining("page=2"));
    expect(wrapper.text()).toContain("陶艺体验");
  });
});
