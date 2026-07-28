<template>
  <aside class="quality" aria-label="资料质量">
    <p class="quality__eyebrow">Content &amp; Quality</p>
    <p class="quality__score">{{ score }}<span>/100</span></p>
    <p>{{ missing.length ? `还需补充：${missing.join('、')}` : '资料已满足完整度检查。' }}</p>
  </aside>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { GiftDraft } from "../../stores/workbench";
const props = defineProps<{ draft: GiftDraft }>();
const missing = computed(() => {
  const fields: [string, boolean][] = [
    ["标准名称", Boolean(props.draft.canonicalName.trim())],
    ["适合对象", props.draft.recipientTypes.length > 0],
    ["适合场景", props.draft.occasions.length > 0],
    ["价格范围", props.draft.priceMin !== null && props.draft.priceMax !== null],
    ["送礼理由", Boolean(props.draft.whyTemplate.trim())],
  ];
  if (props.draft.giftTypeCode === "product") {
    fields.push(["商品形态", Boolean(props.draft.productDetails.productForm)], ["通用商品名", Boolean(props.draft.productDetails.genericProductName)], ["材质", props.draft.productDetails.materials.length > 0], ["配送方式", props.draft.productDetails.shippingRequired !== undefined]);
  } else {
    fields.push(["活动方式", Boolean(props.draft.activityDetails.activityMode)], ["活动时长", props.draft.activityDetails.durationMinutesMin !== null && props.draft.activityDetails.durationMinutesMax !== null], ["参与人数", props.draft.activityDetails.participantsMin !== null && props.draft.activityDetails.participantsMax !== null], ["定价单位", Boolean(props.draft.activityDetails.pricingUnit)]);
  }
  return fields.filter(([, present]) => !present).map(([label]) => label);
});
const score = computed(() => 100 - missing.value.length * 10);
</script>

<style scoped>
.quality { position: sticky; top: 20px; padding: 20px; border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-surface); }.quality__eyebrow { margin: 0; color: var(--color-accent); font-size: .75rem; font-weight: 800; letter-spacing: .08em; }.quality__score { margin: 8px 0; color: var(--color-primary); font-size: 2rem; font-weight: 800; }.quality__score span { font-size: 1rem; }.quality > p:last-child { margin: 0; color: var(--color-ink-muted); font-size: .875rem; line-height: 1.55; }
</style>
