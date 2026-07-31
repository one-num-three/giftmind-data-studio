<template>
  <section class="section" data-section="product" aria-labelledby="product-title">
    <h2 id="product-title">Type-Specific Details · 商品</h2>
    <label>商品形态<select data-product-form :value="modelValue.productForm" @change="setProductForm"><option value="physical">实物</option><option value="digital">数字商品</option><option value="hybrid">混合</option></select></label>
    <label :class="{ 'ai-highlight': highlighted('productDetails.genericProductName') }">通用商品名<input v-model="modelValue.genericProductName" /></label>
    <OptionPicker data-product-materials label="常见材质" field="materials" :options="materialOptions" :selected="modelValue.materials" :ai-highlighted="highlighted('productDetails.materials')" @toggle="toggleList" />
    <label :class="{ 'ai-highlight': highlighted('productDetails.shippingRequired') }"><input v-model="modelValue.shippingRequired" type="checkbox" /> 需要配送</label>
    <OptionPicker data-personalization-methods label="个性化方式" field="personalizationMethods" :options="personalizationOptions" :selected="modelValue.personalizationMethods ?? []" :ai-highlighted="highlighted('productDetails.personalizationMethods')" @toggle="toggleList" />
    <label v-if="modelValue.productForm !== 'physical'">数字交付方式<input data-digital-delivery v-model="modelValue.digitalDeliveryMethod" placeholder="下载链接、兑换码…" /></label>
  </section>
</template>

<script setup lang="ts">
import type { ProductDetailsInput } from "../../api/gifts";
import OptionPicker from "./OptionPicker.vue";

const modelValue = defineModel<ProductDetailsInput>({ required: true });
const props = withDefaults(defineProps<{ highlightedFields?: string[] }>(), { highlightedFields: () => [] });
const materialOptions = ["木质", "金属", "陶瓷", "玻璃", "皮革", "棉麻", "纸张", "塑料", "天然材料"];
const personalizationOptions = ["刻字", "印照片", "颜色可选", "尺寸可选", "包装定制", "图案定制", "贺卡定制"];
function setProductForm(event: Event) {
  modelValue.value = { ...modelValue.value, productForm: (event.target as HTMLSelectElement).value as ProductDetailsInput["productForm"] };
}
function toggleList(field: string, value: string) {
  const key = field as "materials" | "personalizationMethods";
  const current = modelValue.value[key] ?? [];
  modelValue.value[key] = current.includes(value) ? current.filter((item) => item !== value) : [...current, value];
}
function highlighted(path: string) { return props.highlightedFields.includes(path); }
</script>

<style scoped>
.section { display: grid; gap: 14px; }.section > h2 { margin: 0; color: var(--color-ink); font-size: 1rem; }
label { display: grid; gap: 6px; color: var(--color-ink-muted); font-size: .875rem; font-weight: 700; } label:has(input[type="checkbox"]) { display: flex; align-items: center; gap: 8px; }
input:not([type="checkbox"]), select { width: 100%; padding: 10px 12px; border: 1px solid var(--color-border); border-radius: var(--radius-sm); color: var(--color-ink); background: var(--color-surface); }
.ai-highlight { margin: -6px; padding: 6px; border-radius: 12px; background: #eef8f1; box-shadow: 0 0 0 1px #79a98e inset; }
</style>
