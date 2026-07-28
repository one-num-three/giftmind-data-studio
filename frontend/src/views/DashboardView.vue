<template>
  <section class="dashboard" aria-labelledby="dashboard-title">
    <div class="heading"><div><p>资料维护</p><h1 id="dashboard-title">礼物数据</h1><span>快速了解产品与活动资料的维护状态。</span></div><RouterLink :to="{ name: 'gift-create' }">新建礼物</RouterLink></div>
    <section class="metrics" aria-live="polite"><article v-for="metric in metrics" :key="metric.label"><span>{{ metric.label }}</span><strong>{{ metric.value }}</strong></article></section>
    <section class="dashboard__grid"><article class="panel"><h2>资料覆盖</h2><p>商品 {{ summary?.productCount ?? 0 }} · 活动 {{ summary?.activityCount ?? 0 }}</p><RouterLink :to="{ name: 'gift-list' }">查看全部礼物</RouterLink></article><article class="panel"><h2>维护提醒</h2><ul><li>缺少图片：{{ summary?.missingImages ?? 0 }}</li><li>缺少来源：{{ summary?.missingSources ?? 0 }}</li><li>渠道待复核：{{ summary?.staleChannels ?? 0 }}</li><li>可能重复：{{ summary?.possibleDuplicates ?? 0 }}</li></ul><RouterLink :to="{ name: 'recycle-bin' }">打开回收站</RouterLink></article><article class="panel"><h2>最近变更</h2><p v-if="!summary?.recentChanges.length">暂无变更记录。</p><ul v-else><li v-for="event in summary.recentChanges.slice(0, 5)" :key="`${event.entityId}-${event.createdAt}`">{{ event.eventType }} · {{ new Date(event.createdAt).toLocaleString() }}</li></ul></article></section>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { getDashboard } from "../api/gifts";
import type { DashboardSummary } from "../api/gifts";
const summary = ref<DashboardSummary | null>(null);
const metrics = computed(() => [
  { label: "全部", value: summary.value?.total ?? 0 }, { label: "完整", value: summary.value?.complete ?? 0 },
  { label: "草稿", value: summary.value?.drafts ?? 0 }, { label: "待复核", value: summary.value?.needsReview ?? 0 }, { label: "停用", value: summary.value?.inactive ?? 0 },
]);
onMounted(async () => { summary.value = await getDashboard(); });
</script>

<style scoped>
.dashboard { display: grid; gap: 24px; }.heading { display: flex; align-items: end; justify-content: space-between; gap: 18px; }.heading p { margin: 0 0 7px; color: var(--color-accent); font-size: .8125rem; font-weight: 800; letter-spacing: .08em; }.heading h1 { margin: 0 0 8px; color: var(--color-ink); font-size: clamp(2rem, 4vw, 3rem); }.heading span { color: var(--color-ink-muted); }.heading > a, .panel > a { padding: 10px 14px; border-radius: var(--radius-sm); color: white; background: var(--color-primary); font-weight: 800; text-decoration: none; }.metrics { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; }.metrics article, .panel { padding: 16px; border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-surface); }.metrics span { display: block; color: var(--color-ink-muted); font-size: .8125rem; }.metrics strong { color: var(--color-ink); font-size: 1.75rem; }.dashboard__grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }.panel h2 { margin: 0 0 10px; color: var(--color-ink); font-size: 1rem; }.panel p, .panel ul { margin: 0 0 16px; color: var(--color-ink-muted); line-height: 1.7; }.panel ul { padding-left: 20px; }.panel > a { display: inline-block; color: var(--color-primary); background: var(--color-surface-muted); }
@media (max-width: 760px) { .heading { align-items: start; flex-direction: column; }.metrics, .dashboard__grid { grid-template-columns: 1fr 1fr; }.dashboard__grid .panel:last-child { grid-column: 1 / -1; } } @media (max-width: 460px) { .metrics, .dashboard__grid { grid-template-columns: 1fr; }.dashboard__grid .panel:last-child { grid-column: auto; } }
</style>
