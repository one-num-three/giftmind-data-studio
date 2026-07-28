<template>
  <section class="workbench" aria-labelledby="workbench-title">
    <div class="workbench__heading"><div><p>单条礼物录入</p><h1 id="workbench-title">{{ giftId ? '编辑礼物' : '新建礼物' }}</h1></div><span v-if="store.saving">保存中…</span></div>
    <section v-if="restoredDraft" class="restore" aria-live="polite"><strong>发现未完成的本地草稿</strong><span>它只保存在此浏览器，尚未提交。</span><div><button data-action="restore-draft" type="button" @click="restore">恢复草稿</button><button type="button" @click="discardDraft">丢弃</button></div></section>
    <div class="workbench__grid">
      <WorkbenchProgress class="workbench__progress" :sections="sections" current="Basic" />
      <form class="workbench__form" @input="store.markDirty" @submit.prevent="saveAndContinue">
        <section v-if="saveErrors.length" data-save-errors class="feedback feedback--error" role="alert"><strong>请先修正以下问题：</strong><ul><li v-for="error in saveErrors" :key="error">{{ error }}</li></ul></section>
        <section v-if="duplicateMatches.length" data-duplicate-feedback class="feedback" aria-live="polite"><strong>重复记录提示</strong><ul><li v-for="match in duplicateMatches" :key="`${match.canonical_name}-${match.similarity}`">{{ match.exact ? '完全重复' : '相近记录' }}：{{ match.canonical_name }}（相似度 {{ Math.round(match.similarity * 100) }}%）</li></ul></section>
        <CommonFieldsSection v-model="draft" :gift-type-code="draft.giftTypeCode" @suggestion="applyAISuggestion" />
        <GiftTypeSelector :model-value="draft.giftTypeCode" :locked="editingExisting" @select="selectType" />
        <ProductFieldsSection v-if="draft.giftTypeCode === 'product'" v-model="draft.productDetails" />
        <ActivityFieldsSection v-else v-model="draft.activityDetails" />
        <OfferEditor v-model="draft" /><BundleEditor v-model="draft" :exclude-gift-id="giftId" />
        <ImageManager v-if="store.giftId" :gift-id="store.giftId" />
        <div class="actions"><button type="button" @click="saveDraft">保存草稿</button><button type="submit">保存并继续</button><button data-action="save-next" type="button" @click="saveAndCreateNext">保存并新建下一条</button></div>
      </form>
      <QualityPanel class="workbench__quality" :draft="draft" />
    </div>
    <section v-if="pendingType" class="confirm" role="alertdialog" aria-modal="true" aria-labelledby="confirm-title"><div><h2 id="confirm-title">切换礼物类型？</h2><p>{{ discardMessage }}</p><div><button type="button" @click="pendingType = null">保留当前类型</button><button data-action="confirm-type-switch" type="button" @click="confirmType">确认切换</button></div></div></section>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, toRef } from "vue";

import { ApiError } from "../api/client";
import { findGiftDuplicates } from "../api/gifts";
import type { DuplicateMatch, GiftTypeCode } from "../api/gifts";
import type { GiftAISuggestion } from "../api/tools";
import { useDraft } from "../composables/useDraft";
import { useUnsavedChanges } from "../composables/useUnsavedChanges";
import { createActivityDraft, createActivityDetails, createProductDetails, useWorkbenchStore, validateGiftDraft } from "../stores/workbench";
import ActivityFieldsSection from "../components/gifts/ActivityFieldsSection.vue";
import BundleEditor from "../components/gifts/BundleEditor.vue";
import ImageManager from "../components/gifts/ImageManager.vue";
import CommonFieldsSection from "../components/gifts/CommonFieldsSection.vue";
import GiftTypeSelector from "../components/gifts/GiftTypeSelector.vue";
import OfferEditor from "../components/gifts/OfferEditor.vue";
import ProductFieldsSection from "../components/gifts/ProductFieldsSection.vue";
import QualityPanel from "../components/gifts/QualityPanel.vue";
import WorkbenchProgress from "../components/gifts/WorkbenchProgress.vue";

const props = defineProps<{ giftId?: string }>();
const store = useWorkbenchStore();
const draft = computed({ get: () => store.draft, set: (value) => store.replaceDraft(value) });
const draftGiftId = computed(() => props.giftId ?? store.giftId);
const draftEnabled = computed(() => !store.saving);
const editingExisting = computed(() => Boolean(props.giftId || store.giftId));
const { restoredDraft, restoreDraft, discardDraft, clearDraft } = useDraft(draftGiftId, draft, draftEnabled);
const pendingType = ref<GiftTypeCode | null>(null);
const saveErrors = ref<string[]>([]);
const duplicateMatches = ref<DuplicateMatch[]>([]);
const sections = ["Basic", "Type Confirmation", "Matching", "Type-Specific Details", "Concrete Channels", "Content & Quality"];
const discardMessage = computed(() => draft.value.giftTypeCode === "product" ? "商品专属信息不会用于活动记录。确认后将清除商品专属字段。" : "活动专属信息不会用于商品记录。确认后将清除活动专属字段。");

useUnsavedChanges(toRef(store, "dirty"));
onMounted(async () => { if (props.giftId) await store.load(props.giftId); else store.startNew(); });

function hasPopulatedTypeSpecificValue(): boolean {
  const current = draft.value.giftTypeCode === "product" ? draft.value.productDetails : draft.value.activityDetails;
  const defaults = draft.value.giftTypeCode === "product" ? createProductDetails() : createActivityDetails();
  return Object.entries(current).some(([key, value]) => {
    const defaultValue = defaults[key as keyof typeof defaults];
    if (Array.isArray(value)) return value.length > 0;
    if (typeof value === "string") return Boolean(value.trim());
    if (typeof value === "number") return true;
    if (typeof value === "boolean") return value !== defaultValue;
    return value !== null && value !== undefined;
  });
}
function selectType(type: GiftTypeCode) {
  if (editingExisting.value || type === draft.value.giftTypeCode) return;
  if (hasPopulatedTypeSpecificValue()) { pendingType.value = type; return; }
  applyType(type);
}
function commonDraftValues() { const { giftTypeCode: _giftTypeCode, productDetails: _productDetails, activityDetails: _activityDetails, ...common } = draft.value; return common; }
function applyAISuggestion(suggestion: GiftAISuggestion) {
  if (draft.value.giftTypeCode === "product") {
    const current = draft.value.productDetails;
    const details = suggestion.productDetails;
    const arrayFields = ["materials", "colors", "sizes", "personalizationMethods", "deviceOrPlatformCompatibility"] as const;
    const next = { ...current };
    for (const field of arrayFields) {
      const values = details[field];
      if (Array.isArray(values) && values.length) next[field] = [...new Set([...(current[field] ?? []), ...values])];
    }
    for (const [field, value] of Object.entries(details)) {
      if (arrayFields.includes(field as typeof arrayFields[number]) || value === null || value === undefined) continue;
      const currentValue = current[field as keyof typeof current];
      if (currentValue === null || currentValue === undefined || currentValue === "" || (typeof currentValue === "boolean" && currentValue === false)) {
        (next as Record<string, unknown>)[field] = value;
      }
    }
    draft.value.productDetails = next;
    if ((details.personalizationMethods?.length ?? 0) > 0) draft.value.isCustomizable = true;
  } else {
    const current = draft.value.activityDetails;
    const details = suggestion.activityDetails;
    const arrayFields = ["serviceRegions", "includedItems", "excludedItems"] as const;
    const next = { ...current };
    for (const field of arrayFields) {
      const values = details[field];
      if (Array.isArray(values) && values.length) next[field] = [...new Set([...(current[field] ?? []), ...values])];
    }
    for (const [field, value] of Object.entries(details)) {
      if (arrayFields.includes(field as typeof arrayFields[number]) || value === null || value === undefined) continue;
      const currentValue = current[field as keyof typeof current];
      if (currentValue === null || currentValue === undefined || currentValue === "" || (typeof currentValue === "boolean" && currentValue === false)) {
        (next as Record<string, unknown>)[field] = value;
      }
    }
    draft.value.activityDetails = next;
  }
}
function applyType(type: GiftTypeCode) {
  const common = commonDraftValues();
  store.replaceDraft(type === "product" ? { ...common, giftTypeCode: "product", productDetails: createProductDetails() } : { ...common, giftTypeCode: "activity", activityDetails: createActivityDraft().activityDetails });
}
function confirmType() { if (pendingType.value) applyType(pendingType.value); pendingType.value = null; }
function restore() { restoreDraft(); store.markDirty(); }
function duplicateMatchesFrom(error: unknown): DuplicateMatch[] {
  if (!(error instanceof ApiError) || !error.detail || typeof error.detail !== "object") return [];
  const matches = (error.detail as { matches?: unknown }).matches;
  return Array.isArray(matches) ? matches as DuplicateMatch[] : [];
}
async function validateBeforeSave(): Promise<boolean> {
  saveErrors.value = validateGiftDraft(draft.value);
  duplicateMatches.value = [];
  if (saveErrors.value.length) return false;
  if (!editingExisting.value) {
    try { duplicateMatches.value = await findGiftDuplicates(draft.value.canonicalName.trim(), draft.value.aliases); }
    catch { /* a warning lookup must not make a valid save unavailable */ }
    if (duplicateMatches.value.some((match) => match.exact)) { saveErrors.value = ["存在完全重复的礼物记录，请修改名称或别名后再保存。"]; return false; }
  }
  return true;
}
async function save(kind: "draft" | "continue" | "next") {
  if (!await validateBeforeSave()) return;
  try {
    if (kind === "draft") await store.saveDraft();
    else if (kind === "continue") await store.saveAndContinue();
    else await store.saveAndCreateNext();
    clearDraft();
    if (kind === "next") duplicateMatches.value = [];
  } catch (error) {
    duplicateMatches.value = duplicateMatchesFrom(error);
    saveErrors.value = duplicateMatches.value.length ? ["保存时发现重复记录，请查看提示并调整后重试。"] : [error instanceof Error ? `保存失败：${error.message}` : "保存失败，请稍后重试。"];
  }
}
async function saveDraft() { await save("draft"); }
async function saveAndContinue() { await save("continue"); }
async function saveAndCreateNext() { await save("next"); }
</script>

<style scoped>
.workbench { display: grid; gap: 22px; }.workbench__heading { display: flex; align-items: end; justify-content: space-between; gap: 16px; }.workbench__heading p { margin: 0 0 5px; color: var(--color-accent); font-size: .8125rem; font-weight: 800; letter-spacing: .08em; }.workbench__heading h1 { margin: 0; color: var(--color-ink); font-size: 2rem; }.workbench__heading span { color: var(--color-ink-muted); font-size: .875rem; }.workbench__grid { display: grid; grid-template-columns: 190px minmax(0, 1fr) 250px; align-items: start; gap: 20px; }.workbench__form { display: grid; gap: 28px; padding: 26px; border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-surface); box-shadow: var(--shadow-raised); }.actions { display: flex; flex-wrap: wrap; gap: 10px; padding-top: 4px; border-top: 1px solid var(--color-border); }.actions button, .restore button, .confirm button { min-height: 42px; padding: 0 14px; border: 1px solid var(--color-primary); border-radius: var(--radius-sm); color: var(--color-primary); background: var(--color-surface); font-weight: 800; }.actions button:nth-child(2), .actions button:last-child, .restore button:first-child, .confirm button:last-child { color: white; background: var(--color-primary); }.restore { display: flex; align-items: center; gap: 14px; padding: 14px 16px; border: 1px solid var(--color-accent); border-radius: var(--radius-sm); background: #fff8e9; }.restore span { flex: 1; color: var(--color-ink-muted); font-size: .875rem; }.restore div { display: flex; gap: 8px; }.confirm { position: fixed; inset: 0; display: grid; place-items: center; padding: 20px; background: rgb(25 58 44 / .36); }.confirm > div { width: min(440px, 100%); padding: 24px; border-radius: var(--radius-md); background: var(--color-surface); box-shadow: var(--shadow-raised); }.confirm h2 { margin: 0 0 10px; color: var(--color-ink); }.confirm p { margin: 0 0 18px; color: var(--color-ink-muted); line-height: 1.55; }.confirm div div { display: flex; justify-content: end; gap: 10px; }.feedback { padding: 12px 14px; border: 1px solid var(--color-accent); border-radius: var(--radius-sm); background: #fff8e9; color: var(--color-ink); }.feedback--error { border-color: #bd3b32; background: #fff0ef; }.feedback strong { display: block; }.feedback ul { margin: 6px 0 0; padding-left: 20px; }
@media (max-width: 820px) { .workbench__grid { grid-template-columns: 1fr; }.workbench__progress { order: -1; }.workbench__quality { position: static; }.workbench__form { padding: 20px; }.restore { align-items: start; flex-direction: column; }.restore div { width: 100%; } }
</style>
