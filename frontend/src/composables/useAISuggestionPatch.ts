import { ref, watch } from "vue";
import type { Ref } from "vue";

import type { FieldPatch } from "../api/assistant";
import type { GiftDraft } from "../stores/workbench";

const ALLOWED_PATHS = new Set([
  "canonicalName", "giftTypeCode", "shortDescription", "priceMin", "priceMax", "isFree", "whyTemplate",
  "recipientTypes", "occasions", "interests", "tags",
  "productDetails.genericProductName", "productDetails.materials",
  "productDetails.colors", "productDetails.sizes", "productDetails.variantNotes", "productDetails.sizeClass",
  "productDetails.packageDimensions", "productDetails.personalizationMethods", "productDetails.personalizationRequirements",
  "productDetails.shippingRequired", "productDetails.shippingNotes",
  "activityDetails.activityCategory", "activityDetails.serviceRegions",
  "activityDetails.durationMinutesMin", "activityDetails.durationMinutesMax",
  "activityDetails.participantsMin", "activityDetails.participantsMax",
  "activityDetails.bookingRequired", "activityDetails.bookingLeadDaysMin",
  "activityDetails.bookingLeadDaysMax",
]);

function cloneValue<T>(value: T): T {
  if (value === undefined || value === null) return value;
  return JSON.parse(JSON.stringify(value)) as T;
}

function readPath(draft: GiftDraft, path: string): unknown {
  const [section, field] = path.split(".");
  if (!field) return (draft as unknown as Record<string, unknown>)[section];
  return (draft as unknown as Record<string, Record<string, unknown>>)[section]?.[field];
}

function writePath(draft: GiftDraft, path: string, value: unknown): boolean {
  const [section, field] = path.split(".");
  if (!field) {
    (draft as unknown as Record<string, unknown>)[section] = cloneValue(value);
    return true;
  }
  const target = (draft as unknown as Record<string, Record<string, unknown>>)[section];
  if (!target) return false;
  target[field] = cloneValue(value);
  return true;
}

function fingerprint(value: unknown): string {
  return JSON.stringify(value);
}

export function useAISuggestionPatch(
  draft: Ref<GiftDraft>,
  options: { applyType?: (type: "product" | "activity") => boolean } = {},
) {
  const highlightedFields = ref(new Set<string>());
  const previousValues = new Map<string, unknown>();
  const appliedValues = new Map<string, string>();

  function apply(patch: FieldPatch): boolean {
    if (!ALLOWED_PATHS.has(patch.path)) return false;
    if (patch.path === "giftTypeCode") {
      if (!["product", "activity"].includes(String(patch.value))) return false;
      if (options.applyType && !options.applyType(patch.value as "product" | "activity")) return false;
    } else {
      if (!previousValues.has(patch.path)) previousValues.set(patch.path, cloneValue(readPath(draft.value, patch.path)));
      if (!writePath(draft.value, patch.path, patch.value)) return false;
    }
    appliedValues.set(patch.path, fingerprint(readPath(draft.value, patch.path)));
    highlightedFields.value = new Set([...highlightedFields.value, patch.path]);
    return true;
  }

  function applyMany(patches: FieldPatch[], config: { highConfidenceOnly?: boolean } = {}): string[] {
    const applied: string[] = [];
    for (const patch of patches) {
      if (config.highConfidenceOnly && patch.confidence < .8) continue;
      if (apply(patch)) applied.push(patch.path);
    }
    return applied;
  }

  function undo(path: string): boolean {
    if (!previousValues.has(path)) return false;
    const previous = previousValues.get(path);
    if (!writePath(draft.value, path, previous)) return false;
    previousValues.delete(path);
    appliedValues.delete(path);
    const next = new Set(highlightedFields.value);
    next.delete(path);
    highlightedFields.value = next;
    return true;
  }

  function clearHighlight(path: string) {
    const next = new Set(highlightedFields.value);
    next.delete(path);
    highlightedFields.value = next;
    appliedValues.delete(path);
  }

  watch(draft, () => {
    for (const path of highlightedFields.value) {
      if (fingerprint(readPath(draft.value, path)) !== appliedValues.get(path)) clearHighlight(path);
    }
  }, { deep: true });

  return { highlightedFields, apply, applyMany, undo, clearHighlight };
}
