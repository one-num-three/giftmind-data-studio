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
    <OptionPicker label="适合对象" field="recipientTypes" :options="recipientOptions" :selected="modelValue.recipientTypes" @toggle="toggle" />
    <OptionPicker label="适合场景" field="occasions" :options="occasionOptions" :selected="modelValue.occasions" @toggle="toggle" />
    <OptionPicker label="兴趣标签" field="interests" :options="interestOptions" :selected="modelValue.interests" @toggle="toggle" />
    <OptionPicker label="检索标签" field="tags" :options="tagOptions" :selected="modelValue.tags" @toggle="toggle" />
  </section>
</template>

<script setup lang="ts">
import type { CommonGiftDraft } from "../../stores/workbench";
import OptionPicker from "./OptionPicker.vue";

const modelValue = defineModel<CommonGiftDraft>({ required: true });
type ListField = "recipientTypes" | "occasions" | "interests" | "tags";
const recipientOptions = ["自己", "伴侣", "家人", "朋友", "同事", "孩子", "长辈", "老师", "客户"];
const occasionOptions = ["生日", "纪念日", "节日", "毕业", "乔迁", "感谢", "道歉", "日常表达"];
const interestOptions = ["阅读", "运动", "音乐", "美食", "旅行", "科技", "手作", "护肤", "宠物", "游戏"];
const tagOptions = ["实用", "有仪式感", "高性价比", "小众", "可定制", "环保", "适合新手"];
function toggle(field: string, value: string) {
  if (!["recipientTypes", "occasions", "interests", "tags"].includes(field)) return;
  const key = field as ListField;
  const values = modelValue.value[key];
  modelValue.value[key] = values.includes(value) ? values.filter((item) => item !== value) : [...values, value];
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
