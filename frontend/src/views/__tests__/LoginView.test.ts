import { createPinia, setActivePinia } from "pinia";
import { flushPromises, mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import LoginView from "../LoginView.vue";

const { apiRequest } = vi.hoisted(() => ({ apiRequest: vi.fn() }));

vi.mock("../../api/client", () => ({
  apiRequest,
  ApiError: class ApiError extends Error {},
}));

describe("LoginView", () => {
  beforeEach(() => {
    apiRequest.mockReset();
    setActivePinia(createPinia());
  });

  it("logs in with one passcode field and redirects", async () => {
    apiRequest.mockResolvedValue({
      authenticated: true,
      expiresAt: "2026-08-03T00:00:00Z",
    });
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: "/login", name: "login", component: LoginView },
        { path: "/", name: "dashboard", component: { template: "<div />" } },
      ],
    });
    await router.push("/login");
    await router.isReady();
    const wrapper = mount(LoginView, { global: { plugins: [router] } });

    await wrapper.get('input[type="password"]').setValue("team-secret");
    await wrapper.get("form").trigger("submit");
    await flushPromises();

    expect(router.currentRoute.value.name).toBe("dashboard");
  });
});
