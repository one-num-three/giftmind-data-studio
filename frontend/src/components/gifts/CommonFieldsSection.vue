<template>
  <section class="section" data-section="common" aria-labelledby="basic-title">
    <h2 id="basic-title">Basic</h2><button class="ai-button" type="button" :disabled="aiBusy || !modelValue.canonicalName.trim()" @click="runAI">{{ aiBusy ? 'AI 判断中…' : '用 DeepSeek 帮我预填' }}</button><small v-if="aiNotice" data-ai-status class="ai-notice">{{ aiNotice }}</small>
    <div v-if="aiSuggestion" class="ai-summary" data-ai-summary><strong>这次会填入</strong><span>建议类型：{{ aiSuggestion.recommendedGiftTypeCode === 'activity' ? '活动' : '商品' }}</span><span>价格：{{ priceLabel }}</span><span>适合：{{ aiSuggestion.recipientTypes.join('、') || '待确认' }}</span><span>场景：{{ aiSuggestion.occasions.join('、') || '待确认' }}</span><span v-if="aiSuggestion.typeReason">{{ aiSuggestion.typeReason }}</span></div>
    <label :class="{ 'ai-highlight': highlighted('canonicalName') }">标准名称<input data-field="canonical-name" v-model="modelValue.canonicalName" required /></label>
    <label :class="{ 'ai-highlight': highlighted('shortDescription') }">简短说明<textarea data-field="short-description" v-model="modelValue.shortDescription" rows="2" /></label>
    <div class="fields fields--two">
      <label :class="{ 'ai-highlight': highlighted('priceMin') }">最低价格<input data-field="price-min" v-model.number="modelValue.priceMin" type="number" min="0" /></label>
      <label :class="{ 'ai-highlight': highlighted('priceMax') }">最高价格<input data-field="price-max" v-model.number="modelValue.priceMax" type="number" min="0" /></label>
    </div>
    <label :class="{ 'ai-highlight': highlighted('whyTemplate') }">送礼理由<textarea data-field="why-template" v-model="modelValue.whyTemplate" rows="3" /></label>
  </section>

  <section class="section" data-section="matching" aria-labelledby="matching-title">
    <h2 id="matching-title">Matching</h2>
    <OptionPicker label="适合对象" field="recipientTypes" :options="recipientOptions" :selected="modelValue.recipientTypes" :ai-highlighted="highlighted('recipientTypes')" @toggle="toggle" />
    <OptionPicker label="适合场景" field="occasions" :options="occasionOptions" :selected="modelValue.occasions" :ai-highlighted="highlighted('occasions')" @toggle="toggle" />
    <OptionPicker label="兴趣标签" field="interests" :options="interestOptions" :selected="modelValue.interests" :ai-highlighted="highlighted('interests')" @toggle="toggle" />
    <OptionPicker label="检索标签" field="tags" :options="tagOptions" :selected="modelValue.tags" :ai-highlighted="highlighted('tags')" @toggle="toggle" />
  </section>
</template>

<script setup lang="ts">
import type { CommonGiftDraft } from "../../stores/workbench";
import OptionPicker from "./OptionPicker.vue";
import { computed, ref } from "vue";
import type { GiftTypeCode } from "../../api/gifts";
import { suggestGift } from "../../api/tools";
import type { GiftAISuggestion } from "../../api/tools";

const modelValue = defineModel<CommonGiftDraft>({ required: true });
const props = withDefaults(defineProps<{ giftTypeCode?: GiftTypeCode; highlightedFields?: string[] }>(), { giftTypeCode: "product", highlightedFields: () => [] });
const emit = defineEmits<{ suggestion: [suggestion: GiftAISuggestion] }>();
type ListField = "recipientTypes" | "occasions" | "interests" | "tags";
const recipientOptions = ["自己", "伴侣", "家人", "朋友", "同事", "孩子", "长辈", "老师", "客户"];
const occasionOptions = ["生日", "纪念日", "节日", "毕业", "乔迁", "感谢", "道歉", "日常表达"];
const interestOptions = ["阅读", "运动", "音乐", "美食", "旅行", "科技", "手作", "护肤", "宠物", "游戏"];
const tagOptions = ["实用", "有仪式感", "高性价比", "小众", "可定制", "环保", "适合新手"];
const aiBusy = ref(false); const aiNotice = ref(""); const aiSuggestion = ref<GiftAISuggestion | null>(null);
const priceLabel = computed(() => {
  if (!aiSuggestion.value) return "待确认";
  if (aiSuggestion.value.isFree) return "免费";
  if (aiSuggestion.value.priceMin === null && aiSuggestion.value.priceMax === null) return "待确认";
  return `${aiSuggestion.value.priceMin ?? "?"}–${aiSuggestion.value.priceMax ?? "?"} 元`;
});
function mergeList(field: ListField | "relationshipStages" | "ageRanges" | "traits" | "desiredFeelings" | "memoryHooks" | "customTags", values?: string[]) {
  if (!values?.length) return;
  const current = modelValue.value[field];
  modelValue.value[field] = [...new Set([...current, ...values])] as never;
}
function fillText(field: "shortDescription" | "whyTemplate" | "bestScenarios" | "unsuitableScenarios" | "purchaseOrBookingTip" | "ritualTip" | "pairingIdeas", value: string | null | undefined) {
  if (value && !modelValue.value[field]) modelValue.value[field] = value;
}
function applyCommonSuggestion(result: GiftAISuggestion) {
  if (!modelValue.value.subcategoryCode) modelValue.value.subcategoryCode = result.subcategoryCode;
  fillText("shortDescription", result.shortDescription); fillText("whyTemplate", result.whyTemplate);
  fillText("bestScenarios", result.bestScenarios); fillText("unsuitableScenarios", result.unsuitableScenarios);
  fillText("purchaseOrBookingTip", result.purchaseOrBookingTip); fillText("ritualTip", result.ritualTip); fillText("pairingIdeas", result.pairingIdeas);
  if (modelValue.value.priceMin === null && result.priceMin !== null) modelValue.value.priceMin = result.priceMin;
  if (modelValue.value.priceMax === null && result.priceMax !== null) modelValue.value.priceMax = result.priceMax;
  if (result.isFree && modelValue.value.priceMin === null && modelValue.value.priceMax === null) modelValue.value.isFree = true;
  mergeList("recipientTypes", result.recipientTypes); mergeList("relationshipStages", result.relationshipStages); mergeList("ageRanges", result.ageRanges);
  mergeList("traits", result.traits); mergeList("interests", result.interests); mergeList("occasions", result.occasions); mergeList("desiredFeelings", result.desiredFeelings);
  mergeList("memoryHooks", result.memoryHooks); mergeList("tags", result.tags); mergeList("customTags", result.customTags);
}
async function runAI() {
  aiBusy.value = true; aiNotice.value = "";
  try {
    const result = await suggestGift(modelValue.value.canonicalName, props.giftTypeCode, modelValue.value as unknown as Record<string, unknown>);
    aiSuggestion.value = result; applyCommonSuggestion(result); emit("suggestion", result);
    const typeNotice = result.recommendedGiftTypeCode !== props.giftTypeCode ? `模型建议类型为${result.recommendedGiftTypeCode === "activity" ? "活动" : "商品"}，请确认是否切换。` : "";
    aiNotice.value = `${result.source === "deepseek" ? "DeepSeek 完整建议已填入，请人工确认。" : "当前使用规则兜底建议，请人工确认。"}${typeNotice}`;
  } catch { aiNotice.value = "AI 暂时不可用，请继续手动选择。"; } finally { aiBusy.value = false; }
}
function toggle(field: string, value: string) {
  if (!["recipientTypes", "occasions", "interests", "tags"].includes(field)) return;
  const key = field as ListField;
  const values = modelValue.value[key];
  modelValue.value[key] = values.includes(value) ? values.filter((item) => item !== value) : [...values, value];
}
function highlighted(path: string) { return props.highlightedFields.includes(path); }
</script>

<style scoped>
.section { display: grid; gap: 14px; }
h2 { margin: 0; color: var(--color-ink); font-size: 1rem; }.ai-button { justify-self: start; padding: 8px 12px; border: 1px solid var(--color-primary); border-radius: 999px; color: var(--color-primary); background: transparent; font-weight: 800; }.ai-button:disabled { opacity: .5; }.ai-notice { color: var(--color-accent); }
.ai-summary { display: grid; gap: 4px; padding: 10px 12px; border-left: 3px solid var(--color-accent); color: var(--color-ink-muted); background: var(--color-surface-muted); font-size: .82rem; }.ai-summary strong { color: var(--color-ink); }
label { display: grid; gap: 6px; color: var(--color-ink-muted); font-size: .875rem; font-weight: 700; }
input, textarea { width: 100%; padding: 10px 12px; border: 1px solid var(--color-border); border-radius: var(--radius-sm); color: var(--color-ink); background: var(--color-surface); }
.ai-highlight input, .ai-highlight textarea { border-color: #79a98e; background: #eef8f1; box-shadow: 0 0 0 3px rgb(121 169 142 / .14); }
.fields { display: grid; gap: 12px; }.fields--two { grid-template-columns: repeat(2, minmax(0, 1fr)); }
@media (max-width: 520px) { .fields--two { grid-template-columns: 1fr; } }
</style>
