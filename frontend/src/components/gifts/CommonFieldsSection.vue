<template>
  <section class="section" data-section="common" aria-labelledby="basic-title">
    <h2 id="basic-title">Basic</h2>
    <label>标准名称<input data-field="canonical-name" v-model="modelValue.canonicalName" required /></label>
    <label>简短说明<textarea v-model="modelValue.shortDescription" rows="2" /></label>
    <div class="fields fields--two">
      <label>最低价格<input v-model.number="modelValue.priceMin" type="number" min="0" /></label>
      <label>最高价格<input v-model.number="modelValue.priceMax" type="number" min="0" /></label>
    </div>
    <label>送礼理由<textarea v-model="modelValue.whyTemplate" rows="3" /></label>
  </section>

  <section class="section" data-section="matching" aria-labelledby="matching-title">
    <h2 id="matching-title">Matching</h2>
    <label>适合对象（逗号分隔）<input :value="modelValue.recipientTypes.join(', ')" @change="setList('recipientTypes', $event)" /></label>
    <label>适合场景（逗号分隔）<input :value="modelValue.occasions.join(', ')" @change="setList('occasions', $event)" /></label>
    <label>兴趣标签（逗号分隔）<input :value="modelValue.interests.join(', ')" @change="setList('interests', $event)" /></label>
    <label>检索标签（逗号分隔）<input :value="modelValue.tags.join(', ')" @change="setList('tags', $event)" /></label>
  </section>
</template>

<script setup lang="ts">
import type { CommonGiftDraft } from "../../stores/workbench";

const modelValue = defineModel<CommonGiftDraft>({ required: true });
type ListField = "recipientTypes" | "occasions" | "interests" | "tags";
function setList(field: ListField, event: Event) {
  modelValue.value[field] = (event.target as HTMLInputElement).value.split(",").map((item) => item.trim()).filter(Boolean);
}
</script>

<style scoped>
.section { display: grid; gap: 14px; }
h2 { margin: 0; color: var(--color-ink); font-size: 1rem; }
label { display: grid; gap: 6px; color: var(--color-ink-muted); font-size: .875rem; font-weight: 700; }
input, textarea { width: 100%; padding: 10px 12px; border: 1px solid var(--color-border); border-radius: var(--radius-sm); color: var(--color-ink); background: var(--color-surface); }
.fields { display: grid; gap: 12px; }.fields--two { grid-template-columns: repeat(2, minmax(0, 1fr)); }
@media (max-width: 520px) { .fields--two { grid-template-columns: 1fr; } }
</style>
