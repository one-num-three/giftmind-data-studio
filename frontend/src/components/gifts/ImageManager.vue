<template><section class="images"><div><h2>图片</h2><p>可上传商品或活动图片，单张不超过 8MB。</p></div><input type="file" accept="image/jpeg,image/png,image/webp" @change="upload" /><div class="thumbs"><figure v-for="image in images" :key="image.id"><img :src="image.url" :alt="image.filename" /><button type="button" @click="remove(image.id)">删除</button></figure></div><small v-if="message">{{ message }}</small></section></template>
<script setup lang="ts">
import { onMounted, ref } from "vue";
const props = defineProps<{ giftId: string }>(); const images = ref<{ id: string; filename: string; url: string }[]>([]); const message = ref("");
async function load() { try { const response = await fetch(`/api/gifts/${props.giftId}/images`, { credentials: "include" }); if (response.ok) images.value = await response.json(); } catch { images.value = []; } }
async function upload(event: Event) { const file = (event.target as HTMLInputElement).files?.[0]; if (!file) return; try { const form = new FormData(); form.append("file", file); const response = await fetch(`/api/gifts/${props.giftId}/images`, { method: "POST", body: form, credentials: "include" }); message.value = response.ok ? "图片已上传。" : "图片上传失败。"; await load(); } catch { message.value = "本地预览未连接后端，图片稍后可上传。"; } }
async function remove(id: string) { try { await fetch(`/api/images/${id}`, { method: "DELETE", credentials: "include" }); } finally { await load(); } }
onMounted(load);
</script>
<style scoped>.images { display: grid; gap: 10px; }.images h2 { margin: 0; color: var(--color-ink); font-size: 1rem; }.images p, .images small { margin: 0; color: var(--color-ink-muted); }.thumbs { display: flex; flex-wrap: wrap; gap: 10px; }.thumbs figure { position: relative; width: 110px; margin: 0; }.thumbs img { display: block; width: 110px; height: 90px; object-fit: cover; border-radius: var(--radius-sm); }.thumbs button { width: 100%; border: 0; color: var(--color-danger); background: transparent; }</style>
