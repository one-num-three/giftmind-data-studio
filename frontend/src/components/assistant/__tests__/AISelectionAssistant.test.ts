import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({
  createAssistantThread: vi.fn(),
  sendAssistantMessage: vi.fn(),
  uploadAssistantAttachment: vi.fn(),
  reviewSuggestionRun: vi.fn(),
  bindAssistantThread: vi.fn(),
}));
vi.mock("../../../api/assistant", () => api);

import AISelectionAssistant from "../AISelectionAssistant.vue";

describe("AISelectionAssistant", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.createAssistantThread.mockResolvedValue({ id: "thread-1", messages: [], suggestionRuns: [] });
    api.uploadAssistantAttachment.mockResolvedValue({ id: "pic.jpg", name: "pic.jpg", mimeType: "image/jpeg", url: "/uploads/pic.jpg" });
    api.sendAssistantMessage.mockResolvedValue({
      userMessage: { id: "u1", role: "user", content: "识别图片", attachments: [] },
      assistantMessage: { id: "a1", role: "assistant", content: "已生成建议", attachments: [] },
      suggestionRun: { id: "r1", patches: [{ path: "shortDescription", label: "简短说明", value: "一份礼物", confidence: .9, status: "pending" }], appliedFields: [], ignoredFields: [] },
    });
  });

  it("opens a separate draft thread and sends an attached image to DeepSeek suggestions", async () => {
    const wrapper = mount(AISelectionAssistant, { props: { draftId: "11111111-1111-4111-8111-111111111111", giftTypeCode: "product", currentValues: {} } });
    await wrapper.get("[data-ai-toggle]").trigger("click");
    const input = wrapper.get("[data-ai-image-input]").element as HTMLInputElement;
    Object.defineProperty(input, "files", { configurable: true, value: [new File(["photo"], "gift.jpg", { type: "image/jpeg" })] });
    await wrapper.get("[data-ai-image-input]").trigger("change");
    await wrapper.get("[data-ai-message]").setValue("识别图片");
    await wrapper.get("[data-ai-send]").trigger("click");
    await flushPromises();

    expect(api.uploadAssistantAttachment).toHaveBeenCalledWith("thread-1", expect.any(File));
    expect(api.sendAssistantMessage).toHaveBeenCalledWith("thread-1", expect.objectContaining({
      attachments: [expect.objectContaining({ name: "pic.jpg" })],
    }));
    expect(wrapper.text()).toContain("简短说明");
    expect(wrapper.text()).toContain("DeepSeek V4 Flash");
  });
});
