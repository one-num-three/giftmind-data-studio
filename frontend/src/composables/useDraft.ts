import { computed, onBeforeUnmount, ref, watch } from "vue";
import type { Ref } from "vue";

import type { GiftDraft } from "../stores/workbench";

const DRAFT_VERSION = 1;

export function draftStorageKey(giftId: string | null): string {
  return `giftmind.workbench.v${DRAFT_VERSION}.${giftId ?? "new"}`;
}

export function useDraft(giftId: Ref<string | null>, draft: Ref<GiftDraft>, enabled: Ref<boolean>) {
  const key = computed(() => draftStorageKey(giftId.value));
  const restoredDraft = ref<GiftDraft | null>(null);
  const usedKeys = new Set<string>();
  let timer: ReturnType<typeof setTimeout> | undefined;

  function readStoredDraft() {
    const raw = localStorage.getItem(key.value);
    if (!raw) return;
    try {
      const stored = JSON.parse(raw) as { version?: number; draft?: GiftDraft };
      restoredDraft.value = stored.version === DRAFT_VERSION && stored.draft ? stored.draft : null;
    } catch {
      localStorage.removeItem(key.value);
    }
  }

  function restoreDraft() {
    if (restoredDraft.value) draft.value = restoredDraft.value;
    restoredDraft.value = null;
  }

  function discardDraft() {
    localStorage.removeItem(key.value);
    restoredDraft.value = null;
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
      localStorage.setItem(key.value, JSON.stringify({ version: DRAFT_VERSION, draft: draft.value }));
    }, 500);
  }, { deep: true });
  onBeforeUnmount(() => timer && clearTimeout(timer));

  return { restoredDraft, restoreDraft, discardDraft, clearDraft };
}
