<template>
  <section class="gift-list" aria-labelledby="gift-list-title">
    <div class="heading"><div><p>资料发现</p><h1 id="gift-list-title">礼物列表</h1><span>{{ total }} 条记录</span></div><RouterLink :to="{ name: 'gift-create' }">新建礼物</RouterLink></div>
    <GiftFilters :search="filters.q" :gift-type="filters.giftType" :status="filters.status" @update:search="setSearch" @update:gift-type="setFilter('giftType', $event)" @update:status="setFilter('status', $event)" />
    <div class="toolbar"><div><button :class="{ active: view === 'table' }" data-action="table" type="button" @click="setView('table')">表格</button><button :class="{ active: view === 'cards' }" data-action="cards" type="button" @click="setView('cards')">卡片</button></div><div v-if="selectedIds.length" class="bulk"><select v-model="bulkStatus"><option value="active">启用</option><option value="draft">草稿</option><option value="inactive">停用</option></select><button type="button" @click="applyBulkStatus">更新 {{ selectedIds.length }} 条状态</button></div></div>
    <p v-if="notice" class="notice" role="status">{{ notice }}</p>
    <GiftTable v-if="view === 'table'" v-model:selected-ids="selectedIds" :gifts="gifts" @copy="pendingCopy = $event" @delete="removeGift" />
    <GiftCards v-else :gifts="gifts" @copy="pendingCopy = $event" @delete="removeGift" />
    <section v-if="pendingCopy" data-copy-confirm class="dialog" role="alertdialog"><div><h2>复制“{{ pendingCopy.canonicalName }}”？</h2><p>将创建一条新草稿，并清除验证状态。</p><button type="button" @click="pendingCopy = null">取消</button><button data-action="confirm-copy" type="button" @click="confirmCopy">确认复制</button></div></section>
  </section>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { copyGift, deleteGift, listGifts, updateGiftStatus } from "../api/gifts";
import type { GiftRead } from "../api/gifts";
import GiftCards from "../components/gifts/GiftCards.vue";
import GiftFilters from "../components/gifts/GiftFilters.vue";
import GiftTable from "../components/gifts/GiftTable.vue";

const route = useRoute(); const router = useRouter();
const filters = reactive({ q: String(route.query.q ?? ""), giftType: String(route.query.giftType ?? ""), status: String(route.query.status ?? "") });
const view = ref(route.query.view === "cards" || (!route.query.view && window.innerWidth < 720) ? "cards" : "table");
const gifts = ref<GiftRead[]>([]); const total = ref(0); const selectedIds = ref<string[]>([]); const bulkStatus = ref("active"); const pendingCopy = ref<GiftRead | null>(null); const notice = ref("");
let searchTimer: number | undefined;
async function load() { const result = await listGifts({ q: filters.q || undefined, giftType: filters.giftType as "product" | "activity" | undefined, status: filters.status || undefined, deleted: "exclude" }); gifts.value = result.items; total.value = result.total; selectedIds.value = selectedIds.value.filter((id) => gifts.value.some((gift) => gift.id === id)); }
function updateQuery() { router.replace({ query: { ...(filters.q ? { q: filters.q } : {}), ...(filters.giftType ? { giftType: filters.giftType } : {}), ...(filters.status ? { status: filters.status } : {}), ...(view.value === "cards" ? { view: "cards" } : {}) } }); }
async function setFilter(key: "giftType" | "status", value: string) { filters[key] = value; updateQuery(); await load(); }
function setSearch(value: string) { filters.q = value; if (searchTimer) window.clearTimeout(searchTimer); searchTimer = window.setTimeout(async () => { updateQuery(); await load(); }, 250); }
function setView(next: "table" | "cards") { view.value = next; updateQuery(); }
async function confirmCopy() { if (!pendingCopy.value) return; const name = pendingCopy.value.canonicalName; await copyGift(pendingCopy.value.id); pendingCopy.value = null; notice.value = `已复制“${name}”。`; await load(); }
async function removeGift(gift: GiftRead) { await deleteGift(gift.id); notice.value = `已移入回收站：“${gift.canonicalName}”。`; await load(); }
async function applyBulkStatus() { const result = await updateGiftStatus(selectedIds.value, bulkStatus.value); notice.value = `已更新 ${result.affected} 条记录。`; await load(); }
onMounted(load); onBeforeUnmount(() => { if (searchTimer) window.clearTimeout(searchTimer); });
</script>

<style scoped>
.gift-list { display: grid; gap: 18px; }.heading, .toolbar { display: flex; align-items: end; justify-content: space-between; gap: 14px; }.heading p { margin: 0 0 6px; color: var(--color-accent); font-size: .8125rem; font-weight: 800; letter-spacing: .08em; }.heading h1 { margin: 0 0 6px; color: var(--color-ink); font-size: 2rem; }.heading span { color: var(--color-ink-muted); }.heading > a { padding: 10px 14px; border-radius: var(--radius-sm); color: white; background: var(--color-primary); font-weight: 800; text-decoration: none; }.toolbar { align-items: center; }.toolbar button, .bulk select { min-height: 38px; padding: 0 10px; border: 1px solid var(--color-border); border-radius: var(--radius-sm); color: var(--color-primary); background: var(--color-surface); font-weight: 800; }.toolbar button.active, .bulk button { color: white; border-color: var(--color-primary); background: var(--color-primary); }.bulk { display: flex; gap: 8px; }.notice { margin: 0; padding: 10px 12px; border-radius: var(--radius-sm); color: var(--color-primary); background: #e7f3e9; }.dialog { position: fixed; inset: 0; display: grid; place-items: center; padding: 20px; background: rgb(25 58 44 / .36); }.dialog > div { width: min(420px, 100%); padding: 24px; border-radius: var(--radius-md); background: var(--color-surface); box-shadow: var(--shadow-raised); }.dialog h2 { margin: 0 0 10px; color: var(--color-ink); }.dialog p { color: var(--color-ink-muted); }.dialog button { margin-right: 8px; min-height: 40px; padding: 0 12px; border: 1px solid var(--color-primary); border-radius: var(--radius-sm); color: var(--color-primary); background: var(--color-surface); font-weight: 800; }.dialog button:last-child { color: white; background: var(--color-primary); }
@media (max-width: 620px) { .heading, .toolbar { align-items: start; flex-direction: column; }.bulk { flex-wrap: wrap; } }
</style>
