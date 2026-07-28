<template>
  <section class="section" data-section="activity" aria-labelledby="activity-title">
    <h2 id="activity-title">Type-Specific Details · 活动</h2>
    <label>活动方式<select v-model="modelValue.activityMode"><option value="offline">线下</option><option value="online">线上</option><option value="hybrid">混合</option></select></label>
    <label>活动类别<input v-model="modelValue.activityCategory" /></label>
    <label>服务区域（逗号分隔）<input data-service-regions :value="modelValue.serviceRegions.join(', ')" @change="setServiceRegions" /></label>
    <div class="fields"><label>时长（分钟，起）<input v-model.number="modelValue.durationMinutesMin" type="number" min="0" /></label><label>时长（分钟，止）<input v-model.number="modelValue.durationMinutesMax" type="number" min="0" /></label></div>
    <div class="fields"><label>参与人数（起）<input v-model.number="modelValue.participantsMin" type="number" min="0" /></label><label>参与人数（止）<input v-model.number="modelValue.participantsMax" type="number" min="0" /></label></div>
    <label>定价单位<input v-model="modelValue.pricingUnit" placeholder="每人、每场…" /></label>
    <label><input data-booking-required v-model="modelValue.bookingRequired" type="checkbox" /> 需要预约</label>
  </section>
</template>

<script setup lang="ts">
import type { ActivityDetailsInput } from "../../api/gifts";
const modelValue = defineModel<ActivityDetailsInput>({ required: true });
function setServiceRegions(event: Event) {
  modelValue.value.serviceRegions = (event.target as HTMLInputElement).value.split(",").map((item) => item.trim()).filter(Boolean);
}
</script>

<style scoped>
.section { display: grid; gap: 14px; }.section > h2 { margin: 0; color: var(--color-ink); font-size: 1rem; }
label { display: grid; gap: 6px; color: var(--color-ink-muted); font-size: .875rem; font-weight: 700; } label:has(input[type="checkbox"]) { display: flex; align-items: center; gap: 8px; } input, select { width: 100%; padding: 10px 12px; border: 1px solid var(--color-border); border-radius: var(--radius-sm); color: var(--color-ink); background: var(--color-surface); } input[type="checkbox"] { width: auto; }.fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
</style>
