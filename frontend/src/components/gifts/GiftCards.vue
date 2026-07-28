<template>
  <div class="cards" data-view="cards"><article v-for="gift in gifts" :key="gift.id" class="card"><div><span>{{ gift.giftTypeCode === 'product' ? '商品' : '活动' }}</span><strong>{{ gift.emoji }} {{ gift.canonicalName }}</strong></div><p>{{ gift.status }} · 完整度 {{ gift.completenessScore ?? 0 }}%</p><div><button :data-action="`copy-${gift.id}`" type="button" @click="emit('copy', gift)">复制</button><button :data-action="`delete-${gift.id}`" type="button" @click="emit('delete', gift)">删除</button></div></article><p v-if="!gifts.length">没有匹配的礼物。</p></div>
</template>

<script setup lang="ts">
import type { GiftRead } from "../../api/gifts";
defineProps<{ gifts: GiftRead[] }>();
const emit = defineEmits<{ copy: [gift: GiftRead]; delete: [gift: GiftRead] }>();
</script>

<style scoped>
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; }.card { display: grid; gap: 12px; padding: 16px; border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-surface); }.card div:first-child { display: grid; gap: 4px; }.card span, .card p { margin: 0; color: var(--color-ink-muted); font-size: .8125rem; }.card strong { color: var(--color-ink); font-size: 1rem; }.card button { margin-right: 10px; border: 0; color: var(--color-primary); background: transparent; font-weight: 800; }
</style>
