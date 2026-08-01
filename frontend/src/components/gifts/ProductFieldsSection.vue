<template>
  <section class="section" data-section="product" aria-labelledby="product-title">
    <div><p class="eyebrow">类型事实</p><h2 id="product-title">商品信息</h2><small class="helper">只补充页面能确认的规格；其余交给 AI 识别。</small></div>
    <label>商品形态<select data-product-form :value="modelValue.productForm" @change="setProductForm"><option value="physical">实物</option><option value="digital">数字商品</option><option value="hybrid">混合</option></select></label>
    <OptionPicker data-product-colors label="颜色 / 关键规格（可选）" field="colors" :options="colorOptions" :selected="modelValue.colors ?? []" :ai-highlighted="highlighted('productDetails.colors')" @toggle="toggleList" />
    <label :class="{ 'ai-highlight': highlighted('productDetails.variantNotes') }">规格备注（可选）<textarea v-model="modelValue.variantNotes" placeholder="如：直径 5 厘米；有圆形、方形两种款式" /></label>
    <details class="advanced-fields"><summary>商品补充信息 <small>AI 已识别的字段，可展开修改</small></summary>
      <label :class="{ 'ai-highlight': highlighted('productDetails.genericProductName') }">通用商品名<input v-model="modelValue.genericProductName" /></label>
      <OptionPicker data-product-materials label="常见材质" field="materials" :options="materialOptions" :selected="modelValue.materials" :ai-highlighted="highlighted('productDetails.materials')" @toggle="toggleList" />
      <OptionPicker data-product-sizes label="尺寸规格" field="sizes" :options="sizeOptions" :selected="modelValue.sizes ?? []" :ai-highlighted="highlighted('productDetails.sizes')" @toggle="toggleList" />
      <label :class="{ 'ai-highlight': highlighted('productDetails.shippingRequired') }"><input v-model="modelValue.shippingRequired" type="checkbox" /> 需要配送</label>
      <label v-if="modelValue.shippingRequired" :class="{ 'ai-highlight': highlighted('productDetails.shippingNotes') }">配送说明<input v-model="modelValue.shippingNotes" placeholder="如：仅支持国内配送，约 3–5 天" /></label>
      <OptionPicker data-personalization-methods label="个性化方式" field="personalizationMethods" :options="personalizationOptions" :selected="modelValue.personalizationMethods ?? []" :ai-highlighted="highlighted('productDetails.personalizationMethods')" @toggle="toggleList" />
      <label :class="{ 'ai-highlight': highlighted('productDetails.personalizationRequirements') }">定制要求<textarea v-model="modelValue.personalizationRequirements" placeholder="如：需要提供姓名、尺寸或照片" /></label>
      <label v-if="modelValue.productForm !== 'physical'">数字交付方式<input data-digital-delivery v-model="modelValue.digitalDeliveryMethod" placeholder="下载链接、兑换码…" /></label>
    </details>
  </section>
</template>

<script setup lang="ts">
import type { ProductDetailsInput } from "../../api/gifts";
import OptionPicker from "./OptionPicker.vue";

const modelValue = defineModel<ProductDetailsInput>({ required: true });
const props = withDefaults(defineProps<{ highlightedFields?: string[] }>(), { highlightedFields: () => [] });
const materialOptions = ["木质", "金属", "陶瓷", "玻璃", "皮革", "棉麻", "纸张", "塑料", "天然材料"];
const colorOptions = ["红色", "橙色", "黄色", "绿色", "蓝色", "紫色", "黑色", "白色", "金色", "银色", "多色"];
const sizeOptions = ["迷你", "小号", "中号", "大号", "可折叠", "便携"];
const personalizationOptions = ["刻字", "印照片", "颜色可选", "尺寸可选", "包装定制", "图案定制", "贺卡定制"];
function setProductForm(event: Event) {
  modelValue.value = { ...modelValue.value, productForm: (event.target as HTMLSelectElement).value as ProductDetailsInput["productForm"] };
}
function toggleList(field: string, value: string) {
  const key = field as "materials" | "colors" | "sizes" | "personalizationMethods";
  const current = modelValue.value[key] ?? [];
  modelValue.value[key] = current.includes(value) ? current.filter((item) => item !== value) : [...current, value];
}
function highlighted(path: string) { return props.highlightedFields.includes(path); }
</script>

<style scoped>
.section { display: grid; gap: 14px; }.section > div:first-child { display: grid; gap: 4px; }.section > h2 { margin: 0; color: var(--color-ink); font-size: 1rem; }.eyebrow { margin: 0; color: var(--color-accent); font-size: .75rem; font-weight: 800; letter-spacing: .08em; }.helper { color: var(--color-ink-muted); font-size: .82rem; line-height: 1.5; }
label { display: grid; gap: 6px; color: var(--color-ink-muted); font-size: .875rem; font-weight: 700; } label:has(input[type="checkbox"]) { display: flex; align-items: center; gap: 8px; }
input:not([type="checkbox"]), select, textarea { width: 100%; padding: 10px 12px; border: 1px solid var(--color-border); border-radius: var(--radius-sm); color: var(--color-ink); background: var(--color-surface); } textarea { min-height: 72px; resize: vertical; font: inherit; }
.ai-highlight { margin: -6px; padding: 6px; border-radius: 12px; background: #eef8f1; box-shadow: 0 0 0 1px #79a98e inset; }
.advanced-fields { display: grid; gap: 14px; padding: 12px; border: 1px solid var(--color-border); border-radius: var(--radius-sm); background: var(--color-surface-muted); }.advanced-fields summary { cursor: pointer; color: var(--color-primary); font-weight: 800; }.advanced-fields summary small { color: var(--color-ink-muted); font-weight: 500; }
</style>
