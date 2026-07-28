<template>
  <section class="section" data-section="bundle" aria-labelledby="bundle-title">
    <label class="toggle"><input v-model="modelValue.isBundle" type="checkbox" @change="ensureComponent" /> 这是一个组合礼物</label>
    <template v-if="modelValue.isBundle">
      <h2 id="bundle-title">组合内容</h2>
      <p>填写已存在礼物的 UUID；组合中的每项都可单独追溯。</p>
      <label>组件礼物 UUID<input v-model="componentId" @change="syncComponent" /></label>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { CommonGiftDraft } from "../../stores/workbench";
const modelValue = defineModel<CommonGiftDraft>({ required: true });
const componentId = computed({
  get: () => modelValue.value.bundleComponents[0]?.componentGiftId ?? "",
  set: () => undefined,
});
function ensureComponent() {
  if (modelValue.value.isBundle && !modelValue.value.bundleComponents.length) {
    modelValue.value.bundleComponents = [{ componentGiftId: "", quantity: 1, required: true, displayOrder: 0 }];
  }
  if (!modelValue.value.isBundle) modelValue.value.bundleComponents = [];
}
function syncComponent(event: Event) {
  if (!modelValue.value.bundleComponents[0]) return;
  modelValue.value.bundleComponents[0].componentGiftId = (event.target as HTMLInputElement).value.trim();
}
</script>

<style scoped>
.section { display: grid; gap: 10px; }.toggle { display: flex; align-items: center; gap: 8px; color: var(--color-ink); font-weight: 800; }h2, p { margin: 0; }h2 { color: var(--color-ink); font-size: 1rem; }p { color: var(--color-ink-muted); font-size: .875rem; }label:not(.toggle) { display: grid; gap: 6px; color: var(--color-ink-muted); font-size: .875rem; font-weight: 700; }input:not([type="checkbox"]) { width: 100%; padding: 10px 12px; border: 1px solid var(--color-border); border-radius: var(--radius-sm); color: var(--color-ink); background: var(--color-surface); }
</style>
