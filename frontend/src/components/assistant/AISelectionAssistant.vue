<template>
  <button v-if="!open" data-ai-toggle class="ai-launcher" type="button" @click="openAssistant">
    <span>✦</span><strong>AI 选品助手</strong><small>DeepSeek V4 Flash</small>
  </button>
  <aside v-else class="ai-panel" aria-label="AI 选品助手">
    <header>
      <div><strong>AI 选品助手</strong><small>DeepSeek V4 Flash · 当前礼物独立会话</small></div>
      <button data-ai-toggle type="button" aria-label="关闭助手" @click="open = false">×</button>
    </header>

    <div class="ai-messages">
      <div v-if="!messages.length" class="ai-empty">
        <span>✦</span>
        <strong>把资料交给我，我来预填</strong>
        <p>可发送商品名、链接、描述或图片。我会给出类型、价格、匹配对象、送礼理由和细节建议，人工审核后再写入。淘宝/天猫链接会由服务器浏览器读取文字信息，不需要发送账号密码。</p>
      </div>
      <article v-for="message in messages" :key="message.id" :class="['message', `message--${message.role}`]">
        <p>{{ message.content }}</p>
        <div v-if="message.attachments?.length" class="message-images">
          <img v-for="image in message.attachments" :key="image.id" :src="image.url" :alt="image.name" />
        </div>
        <ul v-if="message.sourceRefs?.length" class="message-sources">
          <li v-for="source in message.sourceRefs" :key="source.url || source.label">
            <a v-if="source.url" :href="source.url" target="_blank" rel="noreferrer">{{ source.label || source.url }}</a>
            <span v-else>{{ source.label }}</span>
            <small v-if="source.status && source.status !== 'ok'"> · {{ source.error || source.status }}</small>
          </li>
        </ul>
      </article>
      <section v-for="run in runs" :key="run.id" class="suggestions">
        <div class="suggestions__heading">
          <strong>字段建议</strong>
          <div>
            <button data-ai-apply-all type="button" @click="applyAll(run)">应用全部</button>
            <button type="button" @click="applyHighConfidence(run)">只应用高可信</button>
            <button data-ai-clear-run type="button" @click="clearRun(run)">清除本次</button>
          </div>
        </div>
        <article v-for="patch in run.patches" :key="patch.path" :class="['patch', `patch--${patch.status}`]">
          <div><strong>{{ patch.label }}</strong><small>{{ Math.round(patch.confidence * 100) }}% 可信</small></div>
          <p>{{ formatValue(patch.value) }}</p>
          <small v-if="patch.sourceRefs?.length" class="patch__source">来源：{{ patch.sourceRefs.join('、') }}</small>
          <div class="patch__actions">
            <button v-if="patch.status !== 'applied'" type="button" @click="applyPatch(run, patch)">填入</button>
            <button v-else data-ai-undo type="button" @click="undoPatch(run, patch)">撤销</button>
            <button type="button" :disabled="patch.status === 'ignored'" @click="ignorePatch(run, patch)">忽略</button>
          </div>
        </article>
      </section>
    </div>

    <footer>
      <div v-if="pendingFiles.length" class="pending-images">
        <span v-for="file in pendingFiles" :key="file.name">{{ file.name }} <button type="button" @click="removeFile(file)">×</button></span>
      </div>
      <div v-if="error" class="ai-error" role="alert">{{ error }}</div>
      <textarea data-ai-message v-model="text" rows="3" placeholder="输入名称、链接或描述，也可以直接添加图片…" @keydown.ctrl.enter.prevent="send" />
      <div class="composer-actions">
        <label>
          <input data-ai-image-input type="file" accept="image/jpeg,image/png,image/webp" multiple @change="selectImages" />
          <span>＋ 添加图片</span>
        </label>
        <button data-ai-send type="button" :disabled="sending || (!text.trim() && !pendingFiles.length)" @click="send">
          {{ sending ? "识别中…" : "发送并生成建议" }}
        </button>
      </div>
      <small>最多 4 张，每张不超过 8MB。AI 建议不会自动保存。</small>
    </footer>
  </aside>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";

import {
  bindAssistantThread,
  createAssistantThread,
  reviewSuggestionRun,
  sendAssistantMessage,
  uploadAssistantAttachment,
} from "../../api/assistant";
import type { AssistantMessage, FieldPatch, SuggestionRun } from "../../api/assistant";

const props = defineProps<{
  draftId: string;
  giftId?: string | null;
  giftTypeCode: string;
  currentValues: unknown;
  applyFieldHandler?: (patch: FieldPatch) => boolean;
  undoFieldHandler?: (path: string) => boolean;
}>();
const emit = defineEmits<{ "apply-field": [patch: FieldPatch]; "undo-field": [path: string] }>();
const open = ref(false);
const threadId = ref("");
const text = ref("");
const sending = ref(false);
const error = ref("");
const pendingFiles = ref<File[]>([]);
const messages = ref<AssistantMessage[]>([]);
const runs = ref<SuggestionRun[]>([]);

watch(() => props.draftId, () => {
  threadId.value = "";
  messages.value = [];
  runs.value = [];
  pendingFiles.value = [];
  text.value = "";
});

async function ensureThread() {
  if (threadId.value) return threadId.value;
  const thread = await createAssistantThread(props.draftId, props.giftId);
  threadId.value = thread.id;
  messages.value = thread.messages;
  runs.value = thread.suggestionRuns;
  return thread.id;
}

async function openAssistant() {
  open.value = true;
  error.value = "";
  try { await ensureThread(); } catch (cause) { error.value = cause instanceof Error ? cause.message : "助手加载失败"; }
}

function selectImages(event: Event) {
  error.value = "";
  const files = Array.from((event.target as HTMLInputElement).files ?? []);
  for (const file of files) {
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type) || file.size > 8 * 1024 * 1024) {
      error.value = "仅支持 8MB 内的 JPG、PNG、WebP 图片。";
      continue;
    }
    if (pendingFiles.value.length < 4) pendingFiles.value.push(file);
  }
  (event.target as HTMLInputElement).value = "";
}

function removeFile(file: File) { pendingFiles.value = pendingFiles.value.filter((item) => item !== file); }

async function send() {
  if (sending.value || (!text.value.trim() && !pendingFiles.value.length)) return;
  sending.value = true;
  error.value = "";
  try {
    const id = await ensureThread();
    const attachments = [];
    for (const file of pendingFiles.value) attachments.push(await uploadAssistantAttachment(id, file));
    const turn = await sendAssistantMessage(id, {
      content: text.value.trim(),
      giftTypeCode: props.giftTypeCode,
      currentValues: props.currentValues,
      attachments,
    });
    messages.value.push(turn.userMessage, turn.assistantMessage);
    runs.value.push(turn.suggestionRun);
    text.value = "";
    pendingFiles.value = [];
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "AI 建议生成失败";
  } finally {
    sending.value = false;
  }
}

async function saveReview(run: SuggestionRun) {
  const updated = await reviewSuggestionRun(
    run.id,
    run.patches.filter((item) => item.status === "applied").map((item) => item.path),
    run.patches.filter((item) => item.status === "ignored").map((item) => item.path),
  );
  run.appliedFields = updated.appliedFields;
  run.ignoredFields = updated.ignoredFields;
}

async function applyPatch(run: SuggestionRun, patch: FieldPatch) {
  if (!requestApply(patch)) return;
  patch.status = "applied";
  await saveReview(run);
}

async function ignorePatch(run: SuggestionRun, patch: FieldPatch) {
  patch.status = "ignored";
  await saveReview(run);
}

async function applyHighConfidence(run: SuggestionRun) {
  for (const patch of run.patches.filter((item) => item.status === "pending" && item.confidence >= .8)) {
    if (requestApply(patch)) patch.status = "applied";
  }
  await saveReview(run);
}

async function applyAll(run: SuggestionRun) {
  for (const patch of run.patches.filter((item) => item.status === "pending")) {
    if (requestApply(patch)) patch.status = "applied";
  }
  await saveReview(run);
}

async function undoPatch(run: SuggestionRun, patch: FieldPatch) {
  if (!requestUndo(patch.path)) return;
  patch.status = "pending";
  await saveReview(run);
}

async function clearRun(run: SuggestionRun) {
  for (const patch of run.patches) {
    if (patch.status === "applied") requestUndo(patch.path);
    patch.status = "ignored";
  }
  await saveReview(run);
  runs.value = runs.value.filter((item) => item.id !== run.id);
}

function requestApply(patch: FieldPatch): boolean {
  if (props.applyFieldHandler) return props.applyFieldHandler(patch);
  emit("apply-field", patch);
  return true;
}

function requestUndo(path: string): boolean {
  if (props.undoFieldHandler) return props.undoFieldHandler(path);
  emit("undo-field", path);
  return true;
}

function formatValue(value: unknown) { return Array.isArray(value) ? value.join("、") : typeof value === "boolean" ? (value ? "是" : "否") : String(value); }
async function bindGift(giftId: string) { if (threadId.value) await bindAssistantThread(threadId.value, giftId); }
defineExpose({ bindGift });
</script>

<style scoped>
.ai-launcher { position: fixed; z-index: 20; right: 24px; bottom: 28px; display: grid; grid-template-columns: 34px auto; column-gap: 9px; align-items: center; padding: 11px 16px; border: 0; border-radius: 16px; color: white; background: var(--color-primary); box-shadow: 0 12px 34px rgb(21 58 43 / .28); text-align: left; }.ai-launcher span { grid-row: 1 / 3; display: grid; width: 34px; height: 34px; place-items: center; border-radius: 10px; color: var(--color-primary); background: #f5c85b; font-size: 1.2rem; }.ai-launcher strong { font-size: .9rem; }.ai-launcher small { opacity: .72; font-size: .68rem; }
.ai-panel { position: fixed; z-index: 30; top: 84px; right: 18px; bottom: 18px; display: grid; width: min(390px, calc(100vw - 36px)); grid-template-rows: auto 1fr auto; overflow: hidden; border: 1px solid var(--color-border); border-radius: 20px; background: var(--color-surface); box-shadow: 0 20px 60px rgb(20 45 34 / .25); }.ai-panel header { display: flex; align-items: center; justify-content: space-between; padding: 16px 18px; color: white; background: var(--color-primary); }.ai-panel header div { display: grid; gap: 3px; }.ai-panel header small { opacity: .72; }.ai-panel header button { border: 0; color: white; background: transparent; font-size: 1.7rem; }
.ai-messages { overflow: auto; padding: 16px; background: #f7f5ed; }.ai-empty { padding: 20px 12px; text-align: center; color: var(--color-ink-muted); }.ai-empty span { display: block; color: #d9a829; font-size: 2rem; }.ai-empty strong { display: block; margin: 8px; color: var(--color-ink); }.ai-empty p { font-size: .84rem; line-height: 1.55; }.message { max-width: 86%; margin: 0 0 12px; padding: 10px 12px; border-radius: 14px; background: white; }.message--user { margin-left: auto; color: white; background: var(--color-primary); }.message p { margin: 0; white-space: pre-wrap; }.message-images { display: flex; gap: 6px; margin-top: 8px; }.message-images img { width: 64px; height: 64px; border-radius: 8px; object-fit: cover; }
.message-sources { display: grid; gap: 3px; margin: 8px 0 0; padding-left: 18px; font-size: .72rem; }.message-sources a { color: inherit; overflow-wrap: anywhere; }
.suggestions { display: grid; gap: 8px; margin: 10px 0 18px; }.suggestions__heading { display: grid; gap: 6px; }.suggestions__heading > div { display: flex; flex-wrap: wrap; gap: 4px; }.suggestions__heading button { padding: 3px 5px; border: 0; color: var(--color-primary); background: transparent; font-size: .75rem; font-weight: 700; }.patch { padding: 11px; border: 1px solid #e2dfd2; border-radius: 12px; background: white; }.patch--applied { border-color: #79a98e; background: #eef7f1; }.patch--ignored { opacity: .55; }.patch > div { display: flex; justify-content: space-between; gap: 8px; }.patch small { color: var(--color-ink-muted); }.patch p { margin: 7px 0; color: var(--color-ink); }.patch__source { display: block; margin-bottom: 8px; line-height: 1.4; }.patch__actions { justify-content: flex-end !important; }.patch__actions button { padding: 5px 9px; border: 1px solid var(--color-border); border-radius: 7px; background: white; }
.ai-panel footer { display: grid; gap: 9px; padding: 13px; border-top: 1px solid var(--color-border); background: white; }.ai-panel textarea { width: 100%; resize: none; border: 1px solid var(--color-border); border-radius: 12px; padding: 10px; font: inherit; }.composer-actions { display: flex; justify-content: space-between; gap: 8px; }.composer-actions label { display: inline-flex; align-items: center; padding: 8px 10px; border: 1px solid var(--color-border); border-radius: 9px; color: var(--color-primary); font-weight: 700; cursor: pointer; }.composer-actions input { position: absolute; width: 1px; height: 1px; opacity: 0; }.composer-actions > button { padding: 8px 12px; border: 0; border-radius: 9px; color: white; background: var(--color-primary); font-weight: 800; }.pending-images { display: flex; flex-wrap: wrap; gap: 6px; }.pending-images span { padding: 5px 8px; border-radius: 8px; background: #f2efe4; font-size: .75rem; }.pending-images button { border: 0; background: transparent; }.ai-error { color: #a62d28; font-size: .8rem; }.ai-panel footer > small { color: var(--color-ink-muted); }
@media (max-width: 600px) { .ai-panel { inset: auto 0 0; width: 100%; height: 82vh; border-radius: 20px 20px 0 0; }.ai-launcher { right: 14px; bottom: 16px; } }
</style>
