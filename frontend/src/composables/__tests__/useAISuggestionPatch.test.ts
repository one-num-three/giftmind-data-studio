import { nextTick, ref } from "vue";
import { describe, expect, it } from "vitest";

import type { FieldPatch } from "../../api/assistant";
import { createProductDraft } from "../../stores/workbench";
import { useAISuggestionPatch } from "../useAISuggestionPatch";

function patch(path: string, value: unknown, confidence = .9): FieldPatch {
  return { path, label: path, value, confidence, status: "pending", sourceRefs: ["用户描述"] };
}

describe("useAISuggestionPatch", () => {
  it("applies, highlights, and undoes top-level and nested fields", async () => {
    const draft = ref(createProductDraft());
    const state = useAISuggestionPatch(draft);
    expect(state.apply(patch("priceMin", 39))).toBe(true);
    expect(state.apply(patch("productDetails.materials", ["黄铜"]))).toBe(true);
    await nextTick();

    expect(draft.value.priceMin).toBe(39);
    expect(draft.value.productDetails.materials).toEqual(["黄铜"]);
    expect(state.highlightedFields.value.has("priceMin")).toBe(true);

    expect(state.undo("priceMin")).toBe(true);
    expect(draft.value.priceMin).toBeNull();
    expect(state.highlightedFields.value.has("priceMin")).toBe(false);
  });

  it("applies all or only high-confidence patches and rejects unknown paths", () => {
    const draft = ref(createProductDraft());
    const state = useAISuggestionPatch(draft);
    const patches = [patch("shortDescription", "高可信", .8), patch("whyTemplate", "低可信", .79), patch("unknown", "丢弃", 1)];

    expect(state.applyMany(patches, { highConfidenceOnly: true })).toEqual(["shortDescription"]);
    expect(draft.value.shortDescription).toBe("高可信");
    expect(draft.value.whyTemplate).toBe("");
    expect(state.applyMany(patches)).toEqual(["shortDescription", "whyTemplate"]);
  });

  it("removes the AI highlight after a human changes the applied value", async () => {
    const draft = ref(createProductDraft());
    const state = useAISuggestionPatch(draft);
    state.apply(patch("shortDescription", "AI 说明"));
    await nextTick();
    draft.value.shortDescription = "人工修改";
    await nextTick();
    expect(state.highlightedFields.value.has("shortDescription")).toBe(false);
  });
});
