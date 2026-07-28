<template>
  <main class="login-page" aria-labelledby="login-title">
    <section class="login-card">
      <p class="login-card__eyebrow">GiftMind</p>
      <h1 id="login-title">数据工作台</h1>
      <p class="login-card__description">使用团队口令进入礼物资料库。</p>

      <form class="login-form" @submit.prevent="submit">
        <label for="passcode">团队口令</label>
        <div class="login-form__field">
          <input
            id="passcode"
            v-model="passcode"
            :type="showPasscode ? 'text' : 'password'"
            name="passcode"
            autocomplete="current-password"
            :aria-describedby="error ? 'passcode-error' : undefined"
            required
          />
          <button
            class="login-form__visibility"
            type="button"
            :aria-label="showPasscode ? '隐藏口令' : '显示口令'"
            :aria-pressed="showPasscode"
            @click="showPasscode = !showPasscode"
          >
            {{ showPasscode ? "隐藏" : "显示" }}
          </button>
        </div>
        <p v-if="error" id="passcode-error" class="login-form__error" role="alert">{{ error }}</p>
        <button class="login-form__submit" type="submit" :disabled="submitting">
          {{ submitting ? "正在进入…" : "进入工作台" }}
        </button>
      </form>
    </section>
  </main>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";

import { ApiError } from "../api/client";
import { useSessionStore } from "../stores/session";

const router = useRouter();
const session = useSessionStore();
const passcode = ref("");
const showPasscode = ref(false);
const submitting = ref(false);
const error = ref("");

async function submit() {
  error.value = "";
  submitting.value = true;

  try {
    await session.login(passcode.value);
    await router.replace({ name: "dashboard" });
  } catch (reason) {
    error.value = reason instanceof ApiError && reason.status === 401
      ? "口令不正确，请重试。"
      : "暂时无法进入工作台，请稍后重试。";
  } finally {
    submitting.value = false;
  }
}
</script>

<style scoped>
.login-page {
  display: grid;
  min-height: 100vh;
  place-items: center;
  padding: 32px;
}

.login-card {
  width: min(100%, 440px);
  padding: 40px;
  border: 1px solid var(--color-border);
  border-top: 4px solid var(--color-accent);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  box-shadow: var(--shadow-raised);
}

.login-card__eyebrow {
  margin: 0 0 12px;
  color: var(--color-primary);
  font-size: 0.8125rem;
  font-weight: 800;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

h1 {
  margin: 0;
  color: var(--color-ink);
  font-size: clamp(2rem, 5vw, 2.75rem);
  line-height: 1.15;
}

.login-card__description {
  margin: 14px 0 32px;
  color: var(--color-ink-muted);
  line-height: 1.6;
}

.login-form {
  display: grid;
  gap: 10px;
}

label {
  color: var(--color-ink);
  font-weight: 700;
}

.login-form__field {
  display: flex;
  min-height: 48px;
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: #fff;
}

input {
  width: 100%;
  min-width: 0;
  padding: 0 14px;
  border: 0;
  color: var(--color-ink);
  background: transparent;
}

.login-form__field:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgb(181 139 56 / 0.35);
}

input:focus-visible {
  outline: 0;
}

.login-form__visibility {
  min-width: 56px;
  border: 0;
  border-left: 1px solid var(--color-border);
  color: var(--color-primary);
  background: var(--color-surface-muted);
  font-size: 0.875rem;
  font-weight: 700;
}

.login-form__visibility:hover {
  background: #e5d9c6;
}

.login-form__error {
  margin: 2px 0 0;
  color: var(--color-danger);
  font-size: 0.875rem;
}

.login-form__submit {
  min-height: 48px;
  margin-top: 12px;
  border: 0;
  border-radius: var(--radius-sm);
  color: #fff;
  background: var(--color-primary);
  font-weight: 800;
  transition: background-color 180ms ease;
}

.login-form__submit:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.login-form__submit:disabled {
  cursor: wait;
  opacity: 0.7;
}

@media (max-width: 480px) {
  .login-page {
    padding: 16px;
  }

  .login-card {
    padding: 28px 24px;
  }
}
</style>
