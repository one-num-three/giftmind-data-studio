import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ImageManager from "../ImageManager.vue";

function response(ok: boolean, payload: unknown = {}, status = ok ? 200 : 422) {
  return {
    ok,
    status,
    json: vi.fn().mockResolvedValue(payload),
  };
}

function selectFiles(wrapper: ReturnType<typeof mount>, files: File[]) {
  const input = wrapper.get('[data-image-input]').element as HTMLInputElement;
  Object.defineProperty(input, "files", { configurable: true, value: files });
  return wrapper.get('[data-image-input]').trigger("change");
}

describe("ImageManager", () => {
  const fetchMock = vi.fn();
  const revokeObjectURL = vi.fn();

  beforeEach(() => {
    fetchMock.mockReset();
    revokeObjectURL.mockReset();
    vi.stubGlobal("fetch", fetchMock);
    vi.stubGlobal("URL", {
      ...URL,
      createObjectURL: vi.fn((file: File) => `blob:${file.name}`),
      revokeObjectURL,
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("accepts multiple valid images before a gift has been saved", async () => {
    const wrapper = mount(ImageManager);
    await selectFiles(wrapper, [
      new File(["one"], "front.jpg", { type: "image/jpeg" }),
      new File(["two"], "detail.webp", { type: "image/webp" }),
    ]);

    expect(wrapper.findAll("[data-pending-image]")).toHaveLength(2);
    expect(wrapper.text()).toContain("front.jpg");
    expect(wrapper.text()).toContain("detail.webp");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("rejects unsupported and oversized files before queueing", async () => {
    const wrapper = mount(ImageManager);
    const oversized = new File(["x"], "huge.png", { type: "image/png" });
    Object.defineProperty(oversized, "size", { value: 8 * 1024 * 1024 + 1 });
    await selectFiles(wrapper, [
      new File(["text"], "notes.txt", { type: "text/plain" }),
      oversized,
    ]);

    expect(wrapper.findAll("[data-pending-image]")).toHaveLength(0);
    expect(wrapper.get("[data-image-error]").text()).toContain("JPG、PNG、WebP");
    expect(wrapper.get("[data-image-error]").text()).toContain("8MB");
  });

  it("uploads pending images to the saved gift and clears successful previews", async () => {
    fetchMock.mockResolvedValue(response(true, { id: "image-1" }, 201));
    const wrapper = mount(ImageManager);
    await selectFiles(wrapper, [new File(["one"], "front.jpg", { type: "image/jpeg" })]);

    await (wrapper.vm as unknown as { uploadPending: (giftId: string) => Promise<void> }).uploadPending("gift-1");
    await flushPromises();

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/gifts/gift-1/images",
      expect.objectContaining({ method: "POST", credentials: "include", body: expect.any(FormData) }),
    );
    expect(wrapper.findAll("[data-pending-image]")).toHaveLength(0);
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:front.jpg");
  });

  it("retains failed images with retry feedback", async () => {
    fetchMock.mockResolvedValue(response(false, { detail: "图片上传失败" }, 500));
    const wrapper = mount(ImageManager);
    await selectFiles(wrapper, [new File(["one"], "front.jpg", { type: "image/jpeg" })]);

    await expect((wrapper.vm as unknown as { uploadPending: (giftId: string) => Promise<void> }).uploadPending("gift-1"))
      .rejects.toThrow("1 张图片上传失败");
    await flushPromises();

    expect(wrapper.findAll("[data-pending-image]")).toHaveLength(1);
    expect(wrapper.get("[data-image-error]").text()).toContain("图片上传失败");
    expect(wrapper.text()).toContain("重试上传");
  });
});
