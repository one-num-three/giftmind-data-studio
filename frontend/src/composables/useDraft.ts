import { computed, onBeforeUnmount, ref, watch } from "vue";
import type { Ref } from "vue";

import type { GiftDraft } from "../stores/workbench";

const DRAFT_VERSION = 2;

export function draftStorageKey(giftId: string | null): string {
  return `giftmind.workbench.v${DRAFT_VERSION}.${giftId ?? "new"}`;
}

export function useDraft(
  giftId: Ref<string | null>,
  draft: Ref<GiftDraft>,
  enabled: Ref<boolean>,
  draftId?: Ref<string>,
) {
  const key = computed(() => draftStorageKey(giftId.value));
  const restoredDraft = ref<GiftDraft | null>(null);
  const restoredDraftId = ref<string | null>(null);
  const usedKeys = new Set<string>();
  let timer: ReturnType<typeof setTimeout> | undefined;

  function readStoredDraft() {
    const legacyKey = `giftmind.workbench.v1.${giftId.value ?? "new"}`;
    const raw = localStorage.getItem(key.value) ?? localStorage.getItem(legacyKey);
    if (!raw) return;
    try {
      const stored = JSON.parse(raw) as { version?: number; draft?: GiftDraft; draftId?: string };
      if (stored.draft && (stored.version === DRAFT_VERSION || stored.version === 1)) {
        restoredDraft.value = stored.draft;
        restoredDraftId.value = stored.version === DRAFT_VERSION && stored.draftId ? stored.draftId : draftId?.value ?? null;
        if (stored.version === 1) localStorage.removeItem(legacyKey);
      } else {
        restoredDraft.value = null;
        restoredDraftId.value = null;
      }
    } catch {
      localStorage.removeItem(key.value);
    }
  }

  function restoreDraft() {
    if (restoredDraft.value) draft.value = restoredDraft.value;
    if (draftId && restoredDraftId.value) draftId.value = restoredDraftId.value;
    restoredDraft.value = null;
    restoredDraftId.value = null;
  }

  function discardDraft() {
    localStorage.removeItem(key.value);
    restoredDraft.value = null;
    restoredDraftId.value = null;
  }

  function clearDraft() {
    if (timer) clearTimeout(timer);
    timer = undefined;
    usedKeys.forEach((storageKey) => localStorage.removeItem(storageKey));
  }

  watch(key, (storageKey) => {
    usedKeys.add(storageKey);
    readStoredDraft();
  }, { immediate: true });
  watch(draft, () => {
    if (!enabled.value) return;
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => {
      if (typeof localStorage !== "undefined") {
        localStorage.setItem(key.value, JSON.stringify({ version: DRAFT_VERSION, draftId: draftId?.value, draft: draft.value }));
      }
    }, 500);
  }, { deep: true });
  onBeforeUnmount(() => {
    if (timer) clearTimeout(timer);
    timer = undefined;
  });

  return { restoredDraft, restoredDraftId, restoreDraft, discardDraft, clearDraft };
}
