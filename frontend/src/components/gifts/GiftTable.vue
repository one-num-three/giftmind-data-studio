<template>
  <div class="table-wrap" data-view="table">
    <table>
      <thead><tr><th v-if="selectable"><input aria-label="全选" type="checkbox" :checked="allSelected" @change="toggleAll" /></th><th>礼物</th><th>类型</th><th>状态</th><th>完整度</th><th>操作</th></tr></thead>
      <tbody><tr v-for="gift in gifts" :key="gift.id"><td v-if="selectable"><input :aria-label="`选择${gift.canonicalName}`" type="checkbox" :checked="selectedIds.includes(gift.id)" @change="toggle(gift.id)" /></td><td><RouterLink :to="{ name: 'gift-edit', params: { giftId: gift.id } }">{{ gift.emoji }} {{ gift.canonicalName }}</RouterLink></td><td>{{ gift.giftTypeCode === 'product' ? '商品' : '活动' }}</td><td>{{ gift.status }}</td><td>{{ gift.completenessScore ?? 0 }}%</td><td><button :data-action="`copy-${gift.id}`" type="button" @click="emit('copy', gift)">复制</button><button :data-action="`delete-${gift.id}`" type="button" @click="emit('delete', gift)">删除</button></td></tr><tr v-if="!gifts.length"><td :colspan="selectable ? 6 : 5">没有匹配的礼物。</td></tr></tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { GiftRead } from "../../api/gifts";
const props = withDefaults(defineProps<{ gifts: GiftRead[]; selectedIds?: string[]; selectable?: boolean }>(), { selectedIds: () => [], selectable: true });
const emit = defineEmits<{ "update:selectedIds": [ids: string[]]; copy: [gift: GiftRead]; delete: [gift: GiftRead] }>();
const allSelected = computed(() => props.gifts.length > 0 && props.gifts.every((gift) => props.selectedIds.includes(gift.id)));
function toggle(id: string) { emit("update:selectedIds", props.selectedIds.includes(id) ? props.selectedIds.filter((item) => item !== id) : [...props.selectedIds, id]); }
function toggleAll() { emit("update:selectedIds", allSelected.value ? [] : props.gifts.map((gift) => gift.id)); }
</script>

<style scoped>
.table-wrap { overflow-x: auto; border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-surface); }table { width: 100%; border-collapse: collapse; text-align: left; }th, td { padding: 13px 14px; border-bottom: 1px solid var(--color-border); color: var(--color-ink-muted); font-size: .875rem; }th { color: var(--color-ink); background: var(--color-surface-muted); }tbody tr:last-child td { border-bottom: 0; }a { color: var(--color-primary); font-weight: 800; text-decoration: none; }button { margin-right: 8px; border: 0; color: var(--color-primary); background: transparent; font-weight: 700; }
</style>
