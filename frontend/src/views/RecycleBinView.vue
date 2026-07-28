<template>
  <section class="recycle" aria-labelledby="recycle-title">
    <div class="heading"><div><p>维护工具</p><h1 id="recycle-title">回收站</h1><span>已删除记录可恢复；永久删除不可撤销。</span></div><RouterLink :to="{ name: 'gift-list' }">返回礼物列表</RouterLink></div>
    <p v-if="notice" class="notice" role="status">{{ notice }}</p>
    <div class="table-wrap"><table><thead><tr><th>礼物</th><th>类型</th><th>操作</th></tr></thead><tbody><tr v-for="gift in gifts" :key="gift.id"><td>{{ gift.emoji }} {{ gift.canonicalName }}</td><td>{{ gift.giftTypeCode === 'product' ? '商品' : '活动' }}</td><td><button :data-action="`restore-${gift.id}`" type="button" @click="restore(gift)">恢复</button><button type="button" @click="pendingPurge = gift; typedName = ''">永久删除</button></td></tr><tr v-if="!gifts.length"><td colspan="3">回收站为空。</td></tr></tbody></table></div>
    <nav v-if="total > pageSize" class="pager" aria-label="回收站分页"><button data-action="previous-page" type="button" :disabled="page === 1" @click="page--; load()">上一页</button><span>第 {{ page }} / {{ pageCount }} 页</span><button data-action="next-page" type="button" :disabled="page >= pageCount" @click="page++; load()">下一页</button></nav>
    <section v-if="pendingPurge" class="dialog" role="alertdialog"><div><h2>永久删除“{{ pendingPurge.canonicalName }}”？</h2><p>请输入完整名称以确认。此操作无法撤销。</p><input v-model="typedName" :placeholder="pendingPurge.canonicalName" /><div><button type="button" @click="pendingPurge = null">取消</button><button type="button" :disabled="typedName !== pendingPurge.canonicalName" @click="confirmPurge">永久删除</button></div></div></section>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { listGifts, purgeGift, restoreGift } from "../api/gifts";
import type { GiftRead } from "../api/gifts";
const gifts = ref<GiftRead[]>([]); const total = ref(0); const page = ref(1); const pageSize = 50; const notice = ref(""); const pendingPurge = ref<GiftRead | null>(null); const typedName = ref(""); const pageCount = computed(() => Math.max(1, Math.ceil(total.value / pageSize)));
async function load() { const result = await listGifts({ deleted: "only", page: page.value, pageSize }); gifts.value = result.items; total.value = result.total; }
async function restore(gift: GiftRead) { await restoreGift(gift.id); notice.value = `已恢复“${gift.canonicalName}”。`; await load(); }
async function confirmPurge() { if (!pendingPurge.value || typedName.value !== pendingPurge.value.canonicalName) return; const name = pendingPurge.value.canonicalName; await purgeGift(pendingPurge.value.id, name); pendingPurge.value = null; notice.value = `已永久删除“${name}”。`; if (gifts.value.length === 1 && page.value > 1) page.value--; await load(); }
onMounted(load);
</script>

<style scoped>
.recycle { display: grid; gap: 20px; }.heading { display: flex; align-items: end; justify-content: space-between; gap: 16px; }.heading p { margin: 0 0 6px; color: var(--color-accent); font-size: .8125rem; font-weight: 800; letter-spacing: .08em; }.heading h1 { margin: 0 0 8px; color: var(--color-ink); font-size: 2rem; }.heading span { color: var(--color-ink-muted); }.heading > a { color: var(--color-primary); font-weight: 800; }.notice { margin: 0; padding: 10px 12px; border-radius: var(--radius-sm); color: var(--color-primary); background: #e7f3e9; }.table-wrap { overflow-x: auto; border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-surface); }table { width: 100%; border-collapse: collapse; text-align: left; }th, td { padding: 13px 14px; border-bottom: 1px solid var(--color-border); color: var(--color-ink-muted); }th { color: var(--color-ink); background: var(--color-surface-muted); }tbody tr:last-child td { border-bottom: 0; }td button { margin-right: 8px; border: 0; color: var(--color-primary); background: transparent; font-weight: 800; }.dialog { position: fixed; inset: 0; display: grid; place-items: center; padding: 20px; background: rgb(25 58 44 / .36); }.dialog > div { width: min(420px, 100%); padding: 24px; border-radius: var(--radius-md); background: var(--color-surface); }.dialog h2 { margin-top: 0; color: var(--color-ink); }.dialog p { color: var(--color-ink-muted); }.dialog input { width: 100%; min-height: 42px; margin-bottom: 14px; padding: 0 10px; border: 1px solid var(--color-border); border-radius: var(--radius-sm); }.dialog button { min-height: 40px; margin-right: 8px; padding: 0 12px; border: 1px solid var(--color-primary); border-radius: var(--radius-sm); color: var(--color-primary); background: var(--color-surface); font-weight: 800; }.dialog button:last-child { color: white; background: var(--color-danger); border-color: var(--color-danger); }.dialog button:disabled { opacity: .45; }
@media (max-width: 620px) { .heading { align-items: start; flex-direction: column; } }
</style>
