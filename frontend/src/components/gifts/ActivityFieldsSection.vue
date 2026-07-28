<template>
  <section class="section" data-section="activity" aria-labelledby="activity-title">
    <h2 id="activity-title">Type-Specific Details · 活动</h2>
    <label>活动方式<select v-model="modelValue.activityMode"><option value="offline">线下</option><option value="online">线上</option><option value="hybrid">混合</option></select></label>
    <label>活动类别<select v-model="modelValue.activityCategory"><option value="">请选择</option><option v-for="option in categoryOptions" :key="option" :value="option">{{ option }}</option></select></label>
    <OptionPicker data-service-regions label="服务区域" field="serviceRegions" :options="regionOptions" :selected="modelValue.serviceRegions" @toggle="toggleRegion" />
    <div class="fields"><label>时长（分钟，起）<input v-model.number="modelValue.durationMinutesMin" type="number" min="0" /></label><label>时长（分钟，止）<input v-model.number="modelValue.durationMinutesMax" type="number" min="0" /></label></div>
    <div class="fields"><label>参与人数（起）<input v-model.number="modelValue.participantsMin" type="number" min="0" /></label><label>参与人数（止）<input v-model.number="modelValue.participantsMax" type="number" min="0" /></label></div>
    <label>定价单位<select v-model="modelValue.pricingUnit"><option value="">请选择</option><option value="每人">每人</option><option value="每场">每场</option><option value="每小时">每小时</option><option value="每次">每次</option></select></label>
    <label><input data-booking-required v-model="modelValue.bookingRequired" type="checkbox" /> 需要预约</label>
  </section>
</template>

<script setup lang="ts">
import type { ActivityDetailsInput } from "../../api/gifts";
import OptionPicker from "./OptionPicker.vue";
const modelValue = defineModel<ActivityDetailsInput>({ required: true });
const categoryOptions = ["餐饮美食", "手作体验", "运动健身", "演出展览", "旅行出游", "亲子活动", "课程学习", "休闲娱乐"];
const regionOptions = ["全国通用", "北京", "上海", "广州", "深圳", "南京", "杭州", "成都", "线上"];
function toggleRegion(_field: string, value: string) { modelValue.value.serviceRegions = modelValue.value.serviceRegions.includes(value) ? modelValue.value.serviceRegions.filter((item) => item !== value) : [...modelValue.value.serviceRegions, value]; }
</script>

<style scoped>
.section { display: grid; gap: 14px; }.section > h2 { margin: 0; color: var(--color-ink); font-size: 1rem; }
label { display: grid; gap: 6px; color: var(--color-ink-muted); font-size: .875rem; font-weight: 700; } label:has(input[type="checkbox"]) { display: flex; align-items: center; gap: 8px; } input, select { width: 100%; padding: 10px 12px; border: 1px solid var(--color-border); border-radius: var(--radius-sm); color: var(--color-ink); background: var(--color-surface); } input[type="checkbox"] { width: auto; }.fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
</style>
