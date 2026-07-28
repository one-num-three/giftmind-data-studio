<template>
  <section class="filters" aria-label="礼物筛选">
    <label>搜索<input data-filter="search" :value="search" placeholder="名称或关键词" @input="emit('update:search', ($event.target as HTMLInputElement).value)" /></label>
    <label>类型<select data-filter="gift-type" :value="giftType" @change="emit('update:giftType', ($event.target as HTMLSelectElement).value)"><option value="">全部</option><option value="product">商品</option><option value="activity">活动</option></select></label>
    <label>状态<select data-filter="status" :value="status" @change="emit('update:status', ($event.target as HTMLSelectElement).value)"><option value="">全部</option><option value="draft">草稿</option><option value="active">启用</option><option value="inactive">停用</option></select></label>
  </section>
</template>

<script setup lang="ts">
defineProps<{ search: string; giftType: string; status: string }>();
const emit = defineEmits<{ "update:search": [value: string]; "update:giftType": [value: string]; "update:status": [value: string] }>();
</script>

<style scoped>
.filters { display: grid; grid-template-columns: minmax(180px, 1fr) repeat(2, minmax(120px, .45fr)); gap: 12px; }.filters label { display: grid; gap: 5px; color: var(--color-ink-muted); font-size: .8125rem; font-weight: 700; }.filters input, .filters select { width: 100%; min-height: 42px; padding: 0 10px; border: 1px solid var(--color-border); border-radius: var(--radius-sm); color: var(--color-ink); background: var(--color-surface); }
@media (max-width: 620px) { .filters { grid-template-columns: 1fr; } }
</style>
