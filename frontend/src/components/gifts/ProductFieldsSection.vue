<template>
  <section class="section" data-section="product" aria-labelledby="product-title">
    <h2 id="product-title">Type-Specific Details · 商品</h2>
    <label>商品形态<select v-model="modelValue.productForm"><option value="physical">实物</option><option value="digital">数字商品</option><option value="hybrid">混合</option></select></label>
    <label>通用商品名<input v-model="modelValue.genericProductName" /></label>
    <label>材质（逗号分隔）<input data-product-materials :value="modelValue.materials.join(', ')" @change="setMaterials" /></label>
    <label><input v-model="modelValue.shippingRequired" type="checkbox" /> 需要配送</label>
    <label v-if="modelValue.productForm !== 'physical'">数字交付方式<input v-model="modelValue.digitalDeliveryMethod" placeholder="下载链接、兑换码…" /></label>
  </section>
</template>

<script setup lang="ts">
import type { ProductDetailsInput } from "../../api/gifts";

const modelValue = defineModel<ProductDetailsInput>({ required: true });
function setMaterials(event: Event) {
  modelValue.value.materials = (event.target as HTMLInputElement).value.split(",").map((item) => item.trim()).filter(Boolean);
}
</script>

<style scoped>
.section { display: grid; gap: 14px; }.section > h2 { margin: 0; color: var(--color-ink); font-size: 1rem; }
label { display: grid; gap: 6px; color: var(--color-ink-muted); font-size: .875rem; font-weight: 700; } label:has(input[type="checkbox"]) { display: flex; align-items: center; gap: 8px; }
input:not([type="checkbox"]), select { width: 100%; padding: 10px 12px; border: 1px solid var(--color-border); border-radius: var(--radius-sm); color: var(--color-ink); background: var(--color-surface); }
</style>
