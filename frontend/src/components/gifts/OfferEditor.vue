<template>
  <section class="section" data-section="channels" aria-labelledby="channels-title">
    <h2 id="channels-title">Concrete Channels</h2>
    <p>记录可直接购买或预约的链接，每行一个。</p>
    <textarea :value="modelValue.channels.join('\n')" rows="3" placeholder="https://…" @change="setChannels" />
    <label>来源备注<textarea v-model="modelValue.sourceNotes" rows="2" /></label>
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
.section { display: grid; gap: 10px; }.section > h2 { margin: 0; color: var(--color-ink); font-size: 1rem; }p { margin: 0; color: var(--color-ink-muted); font-size: .875rem; }label { display: grid; gap: 6px; color: var(--color-ink-muted); font-size: .875rem; font-weight: 700; }textarea { width: 100%; padding: 10px 12px; border: 1px solid var(--color-border); border-radius: var(--radius-sm); color: var(--color-ink); background: var(--color-surface); }
</style>
