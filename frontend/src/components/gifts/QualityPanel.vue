<template>
  <aside class="quality" aria-label="资料质量">
    <p class="quality__eyebrow">录入进度</p>
    <p class="quality__score">{{ score }}<span>/100</span></p>
    <p>{{ missing.length ? `人工事实还需：${missing.join('、')}` : '人工需要确认的事实已经齐了。' }}</p>
    <p class="quality__hint">对象、场景、理由和标签由 AI 生成后再审核，不会因为暂时留空阻碍采集。</p>
  </aside>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { GiftDraft } from "../../stores/workbench";
const props = defineProps<{ draft: GiftDraft }>();
const missing = computed(() => {
  const fields: [string, boolean][] = [
    ["标准名称", Boolean(props.draft.canonicalName.trim())],
    ["价格范围", props.draft.isFree || (props.draft.priceMin !== null && props.draft.priceMax !== null)],
  ];
  if (props.draft.giftTypeCode === "product") {
    fields.push(["商品形态", Boolean(props.draft.productDetails.productForm)]);
  } else {
    fields.push(["活动方式", Boolean(props.draft.activityDetails.activityMode)]);
  }
  return fields.filter(([, present]) => !present).map(([label]) => label);
});
const score = computed(() => {
  const total = props.draft.giftTypeCode === "product" ? 3 : 3;
  return Math.round(((total - missing.value.length) / total) * 100);
});
</script>

<style scoped>
.quality { position: sticky; top: 20px; padding: 20px; border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-surface); }.quality__eyebrow { margin: 0; color: var(--color-accent); font-size: .75rem; font-weight: 800; letter-spacing: .08em; }.quality__score { margin: 8px 0; color: var(--color-primary); font-size: 2rem; font-weight: 800; }.quality__score span { font-size: 1rem; }.quality > p:not(.quality__eyebrow):not(.quality__score) { margin: 0; color: var(--color-ink-muted); font-size: .875rem; line-height: 1.55; }.quality__hint { margin-top: 10px !important; padding-top: 10px; border-top: 1px solid var(--color-border); font-size: .78rem !important; }
</style>
