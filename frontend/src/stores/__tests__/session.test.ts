import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { setUnauthorizedHandler } from "../../api/client";
import { useSessionStore } from "../session";

describe("session restoration", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("finishes unauthenticated without invoking the global unauthorized handler", async () => {
    const unauthorizedHandler = vi.fn();
    setUnauthorizedHandler(unauthorizedHandler);
    vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify({ detail: "Not authenticated" }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    }));

    const session = useSessionStore();
    await session.restore();

    expect(session.authenticated).toBe(false);
    expect(session.expiresAt).toBeNull();
    expect(session.restored).toBe(true);
    expect(unauthorizedHandler).not.toHaveBeenCalled();
  });
});
