<template>
  <section class="section" data-section="bundle" aria-labelledby="bundle-title">
    <label class="toggle"><input v-model="modelValue.isBundle" type="checkbox" @change="ensureComponent" /> 这是一个组合礼物</label>
    <template v-if="modelValue.isBundle">
      <h2 id="bundle-title">组合内容</h2>
      <p>从现有的商品或活动记录中选择组件；组件会保留各自的类型和名称。</p>
      <label>组件礼物<select :value="componentId" @change="syncComponent"><option value="" disabled>选择已有礼物</option><option v-for="gift in componentOptions" :key="gift.id" :value="gift.id">{{ gift.giftTypeCode === 'product' ? '商品' : '活动' }} · {{ gift.canonicalName }}</option></select></label>
      <p v-if="loading">正在加载可选礼物…</p><p v-else-if="loadError">无法加载可选礼物，请稍后重试。</p>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { listGifts } from "../../api/gifts";
import type { GiftRead } from "../../api/gifts";
import type { CommonGiftDraft } from "../../stores/workbench";
const modelValue = defineModel<CommonGiftDraft>({ required: true });
const componentOptions = ref<GiftRead[]>([]); const loading = ref(false); const loadError = ref(false);
const componentId = computed(() => modelValue.value.bundleComponents[0]?.componentGiftId ?? "");
function ensureComponent() { if (modelValue.value.isBundle && !modelValue.value.bundleComponents.length) modelValue.value.bundleComponents = [{ componentGiftId: "", quantity: 1, required: true, displayOrder: 0 }]; if (!modelValue.value.isBundle) modelValue.value.bundleComponents = []; }
function syncComponent(event: Event) { const gift = componentOptions.value.find((item) => item.id === (event.target as HTMLSelectElement).value); if (!gift || !modelValue.value.bundleComponents[0]) return; modelValue.value.bundleComponents[0] = { ...modelValue.value.bundleComponents[0], componentGiftId: gift.id, componentTypeCode: gift.giftTypeCode, componentName: gift.canonicalName }; }
async function loadOptions() { loading.value = true; loadError.value = false; try { componentOptions.value = (await listGifts({ deleted: "exclude", pageSize: 100 })).items; } catch { loadError.value = true; } finally { loading.value = false; } }
watch(() => modelValue.value.isBundle, (isBundle) => { if (isBundle && !componentOptions.value.length) void loadOptions(); });
</script>

<style scoped>
.section { display: grid; gap: 10px; }.toggle { display: flex; align-items: center; gap: 8px; color: var(--color-ink); font-weight: 800; }h2, p { margin: 0; }h2 { color: var(--color-ink); font-size: 1rem; }p { color: var(--color-ink-muted); font-size: .875rem; }label:not(.toggle) { display: grid; gap: 6px; color: var(--color-ink-muted); font-size: .875rem; font-weight: 700; }select { width: 100%; padding: 10px 12px; border: 1px solid var(--color-border); border-radius: var(--radius-sm); color: var(--color-ink); background: var(--color-surface); }
</style>
