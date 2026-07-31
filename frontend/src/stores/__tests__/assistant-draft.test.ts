import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import { useWorkbenchStore } from "../workbench";

describe("workbench assistant draft identity", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("keeps one identity for a draft and rotates it for the next gift", () => {
    const store = useWorkbenchStore();
    const first = store.draftId;
    expect(first).toMatch(/^[0-9a-f-]{36}$/);
    store.markDirty();
    expect(store.draftId).toBe(first);
    store.startNew();
    expect(store.draftId).not.toBe(first);
  });
});
