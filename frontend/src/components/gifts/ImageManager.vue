<template>
  <section class="images" aria-labelledby="gift-images-title">
    <div class="images__heading">
      <div>
        <h2 id="gift-images-title">礼物图片</h2>
        <p>支持 JPG、PNG、WebP，单张不超过 8MB，可一次选择多张。</p>
      </div>
      <label class="images__picker">
        <span>＋ 添加图片</span>
        <input
          data-image-input
          type="file"
          accept="image/jpeg,image/png,image/webp"
          multiple
          @change="selectImages"
        />
      </label>
    </div>

    <p v-if="!giftId && pending.length" class="images__notice">
      图片将在保存这条礼物后自动上传，请不要在保存前刷新页面。
    </p>

    <div v-if="images.length || pending.length" class="thumbs">
      <figure v-for="image in images" :key="image.id" class="thumb">
        <img :src="image.url" :alt="image.filename" />
        <figcaption>
          <span :title="image.filename">{{ image.filename }}</span>
          <small>已上传</small>
        </figcaption>
        <button type="button" :disabled="deletingId === image.id" @click="removeServerImage(image.id)">
          {{ deletingId === image.id ? "删除中…" : "删除" }}
        </button>
      </figure>

      <figure
        v-for="image in pending"
        :key="image.id"
        data-pending-image
        class="thumb"
        :class="{ 'thumb--error': image.status === 'error' }"
      >
        <img :src="image.previewUrl" :alt="image.file.name" />
        <figcaption>
          <span :title="image.file.name">{{ image.file.name }}</span>
          <small>{{ formatSize(image.file.size) }} · {{ pendingStatus(image) }}</small>
        </figcaption>
        <button type="button" :disabled="image.status === 'uploading'" @click="removePending(image.id)">
          移除
        </button>
      </figure>
    </div>

    <div v-else class="images__empty">
      <span aria-hidden="true">▧</span>
      <p>还没有图片。商品正面、细节、包装或活动现场图都可以添加。</p>
    </div>

    <div v-if="errorMessage" data-image-error class="images__feedback images__feedback--error" role="alert">
      {{ errorMessage }}
    </div>
    <div v-else-if="message" class="images__feedback" aria-live="polite">{{ message }}</div>

    <button
      v-if="pending.some((image) => image.status === 'error') && uploadGiftId"
      class="images__retry"
      type="button"
      @click="retryUpload"
    >
      重试上传
    </button>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";

interface ServerImage {
  id: string;
  filename: string;
  url: string;
}

interface PendingImage {
  id: string;
  file: File;
  previewUrl: string;
  status: "pending" | "uploading" | "error";
  error: string;
}

const props = defineProps<{ giftId?: string }>();
const images = ref<ServerImage[]>([]);
const pending = ref<PendingImage[]>([]);
const validationErrors = ref<string[]>([]);
const message = ref("");
const deletingId = ref<string | null>(null);
const uploadGiftId = ref<string | null>(props.giftId ?? null);
const acceptedTypes = new Set(["image/jpeg", "image/png", "image/webp"]);
const maxFileSize = 8 * 1024 * 1024;

const errorMessage = computed(() => {
  const uploadErrors = pending.value
    .filter((image) => image.status === "error" && image.error)
    .map((image) => `${image.file.name}：${image.error}`);
  return [...validationErrors.value, ...uploadErrors].join("；");
});

async function load(): Promise<void> {
  if (!props.giftId) {
    images.value = [];
    return;
  }
  try {
    const response = await fetch(`/api/gifts/${props.giftId}/images`, { credentials: "include" });
    if (!response.ok) throw new Error("图片列表加载失败");
    images.value = await response.json() as ServerImage[];
  } catch {
    images.value = [];
    message.value = "暂时无法加载已上传图片。";
  }
}

async function selectImages(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement;
  const files = Array.from(input.files ?? []);
  validationErrors.value = [];
  message.value = "";

  for (const file of files) {
    if (!acceptedTypes.has(file.type)) {
      validationErrors.value.push(`${file.name} 不是 JPG、PNG、WebP 图片`);
      continue;
    }
    if (file.size > maxFileSize) {
      validationErrors.value.push(`${file.name} 超过 8MB`);
      continue;
    }
    pending.value.push({
      id: globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`,
      file,
      previewUrl: URL.createObjectURL(file),
      status: "pending",
      error: "",
    });
  }
  input.value = "";

  if (props.giftId && pending.value.length) {
    try {
      await uploadPending(props.giftId);
    } catch {
      // Individual failures remain visible and can be retried.
    }
  }
}

async function uploadPending(giftId: string): Promise<void> {
  uploadGiftId.value = giftId;
  const candidates = pending.value.filter((image) => image.status !== "uploading");
  if (!candidates.length) return;

  let failed = 0;
  message.value = "";
  validationErrors.value = [];

  for (const image of candidates) {
    image.status = "uploading";
    image.error = "";
    const form = new FormData();
    form.append("file", image.file);
    try {
      const response = await fetch(`/api/gifts/${giftId}/images`, {
        method: "POST",
        body: form,
        credentials: "include",
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => null) as { detail?: string } | null;
        throw new Error(payload?.detail || "图片上传失败");
      }
      URL.revokeObjectURL(image.previewUrl);
      pending.value = pending.value.filter((candidate) => candidate.id !== image.id);
    } catch (error) {
      image.status = "error";
      image.error = error instanceof Error ? error.message : "图片上传失败";
      failed += 1;
    }
  }

  await load();
  if (failed) throw new Error(`${failed} 张图片上传失败，请重试。`);
  message.value = `${candidates.length} 张图片已上传。`;
}

function removePending(id: string): void {
  const image = pending.value.find((candidate) => candidate.id === id);
  if (image) URL.revokeObjectURL(image.previewUrl);
  pending.value = pending.value.filter((candidate) => candidate.id !== id);
  validationErrors.value = [];
}

function clearPending(): void {
  for (const image of pending.value) URL.revokeObjectURL(image.previewUrl);
  pending.value = [];
  validationErrors.value = [];
  message.value = "";
}

function hasPending(): boolean {
  return pending.value.length > 0;
}

async function retryUpload(): Promise<void> {
  if (!uploadGiftId.value) return;
  try {
    await uploadPending(uploadGiftId.value);
  } catch {
    // uploadPending stores field-level feedback.
  }
}

async function removeServerImage(id: string): Promise<void> {
  deletingId.value = id;
  message.value = "";
  try {
    const response = await fetch(`/api/images/${id}`, { method: "DELETE", credentials: "include" });
    if (!response.ok) throw new Error("删除失败");
    message.value = "图片已删除。";
  } catch {
    message.value = "图片删除失败，请重试。";
  } finally {
    deletingId.value = null;
    await load();
  }
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.ceil(bytes / 1024)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function pendingStatus(image: PendingImage): string {
  if (image.status === "uploading") return "上传中";
  if (image.status === "error") return "上传失败";
  return "等待保存";
}

watch(() => props.giftId, load, { immediate: true });
onBeforeUnmount(clearPending);
defineExpose({ uploadPending, clearPending, hasPending });
</script>

<style scoped>
.images { display: grid; gap: 14px; }
.images__heading { display: flex; align-items: start; justify-content: space-between; gap: 16px; }
.images h2 { margin: 0 0 5px; color: var(--color-ink); font-size: 1rem; }
.images p { margin: 0; color: var(--color-ink-muted); line-height: 1.5; }
.images__picker { position: relative; flex: none; display: inline-flex; min-height: 40px; align-items: center; padding: 0 14px; overflow: hidden; border: 1px solid var(--color-primary); border-radius: var(--radius-sm); color: var(--color-primary); background: var(--color-surface); font-weight: 800; cursor: pointer; }
.images__picker input { position: absolute; width: 1px; height: 1px; opacity: 0; }
.images__notice { padding: 10px 12px; border-radius: var(--radius-sm); background: #fff8e9; font-size: .875rem; }
.images__empty { display: flex; align-items: center; gap: 12px; padding: 18px; border: 1px dashed var(--color-border); border-radius: var(--radius-sm); background: color-mix(in srgb, var(--color-surface) 88%, var(--color-primary) 12%); }
.images__empty > span { display: grid; width: 38px; height: 38px; place-items: center; border-radius: 10px; color: var(--color-primary); background: var(--color-surface); font-size: 1.35rem; }
.thumbs { display: grid; grid-template-columns: repeat(auto-fill, minmax(132px, 1fr)); gap: 12px; }
.thumb { min-width: 0; margin: 0; overflow: hidden; border: 1px solid var(--color-border); border-radius: var(--radius-sm); background: var(--color-surface); }
.thumb--error { border-color: var(--color-danger); }
.thumb img { display: block; width: 100%; aspect-ratio: 4 / 3; object-fit: cover; background: #eef1ed; }
.thumb figcaption { display: grid; gap: 2px; padding: 8px 9px 4px; }
.thumb figcaption span { overflow: hidden; color: var(--color-ink); font-size: .8125rem; font-weight: 700; text-overflow: ellipsis; white-space: nowrap; }
.thumb figcaption small { color: var(--color-ink-muted); }
.thumb button { width: 100%; padding: 7px; border: 0; color: var(--color-danger); background: transparent; cursor: pointer; }
.images__feedback { padding: 10px 12px; border-radius: var(--radius-sm); color: var(--color-primary); background: #edf6ef; font-size: .875rem; }
.images__feedback--error { color: var(--color-danger); background: #fff0ef; }
.images__retry { justify-self: start; min-height: 38px; padding: 0 13px; border: 1px solid var(--color-primary); border-radius: var(--radius-sm); color: white; background: var(--color-primary); font-weight: 800; }
@media (max-width: 560px) { .images__heading { flex-direction: column; }.images__picker { width: 100%; justify-content: center; } }
</style>
