<template>
  <section class="section" data-section="channels" aria-labelledby="channels-title">
    <div><p class="eyebrow">可核验来源</p><h2 id="channels-title">来源与备注</h2><small>把商品或活动页面链接放在这里，AI 才能基于原始资料判断。</small></div>
    <textarea data-field="source-urls" :value="modelValue.channels.join('\n')" rows="3" placeholder="每行一个 https://…" @change="setChannels" />
    <label>来源备注<textarea v-model="modelValue.sourceNotes" rows="2" placeholder="例如：页面价格为活动价，采集于 2026-07-31" /></label>
  </section>
</template>

<script setup lang="ts">
import type { CommonGiftDraft } from "../../stores/workbench";
const modelValue = defineModel<CommonGiftDraft>({ required: true });
function setChannels(event: Event) {
  modelValue.value.channels = (event.target as HTMLTextAreaElement).value.split("\n").map((item) => item.trim()).filter(Boolean);
}
</script>

<style scoped>
.section { display: grid; gap: 10px; }.section > div:first-child { display: grid; gap: 4px; }.section > h2 { margin: 0; color: var(--color-ink); font-size: 1rem; }.eyebrow { margin: 0; color: var(--color-accent); font-size: .75rem; font-weight: 800; letter-spacing: .08em; }p, small { margin: 0; color: var(--color-ink-muted); font-size: .875rem; line-height: 1.5; }label { display: grid; gap: 6px; color: var(--color-ink-muted); font-size: .875rem; font-weight: 700; }textarea { width: 100%; padding: 10px 12px; border: 1px solid var(--color-border); border-radius: var(--radius-sm); color: var(--color-ink); background: var(--color-surface); }
</style>
