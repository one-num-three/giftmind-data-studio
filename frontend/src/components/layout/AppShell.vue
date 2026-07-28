<template>
  <div class="shell">
    <header class="shell__header">
      <div class="shell__bar">
        <RouterLink class="shell__brand" :to="{ name: 'dashboard' }">GiftMind</RouterLink>
        <div class="shell__context">
          <RouterLink to="/tools">数据工具</RouterLink><span>数据工作台</span>
          <button class="shell__logout" type="button" @click="handleLogout">退出</button>
        </div>
      </div>
    </header>
    <main class="shell__main">
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from "vue-router";

import { useSessionStore } from "../../stores/session";

const router = useRouter();
const session = useSessionStore();

async function handleLogout() {
  await session.logout();
  await router.replace({ name: "login" });
}
</script>

<style scoped>
.shell {
  min-height: 100vh;
}

.shell__header {
  border-bottom: 1px solid var(--color-border);
  background: rgb(255 253 248 / 0.94);
}

.shell__bar,
.shell__main {
  width: min(var(--content-width), calc(100% - 48px));
  margin: 0 auto;
}

.shell__bar {
  display: flex;
  min-height: 72px;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}

.shell__brand {
  color: var(--color-primary);
  font-size: 1.125rem;
  font-weight: 800;
  letter-spacing: -0.02em;
  text-decoration: none;
}

.shell__context {
  display: flex;
  align-items: center;
  gap: 20px;
  color: var(--color-ink-muted);
  font-size: 0.9375rem;
}

.shell__logout {
  min-height: 44px;
  padding: 0 14px;
  border: 0;
  border-radius: var(--radius-sm);
  color: var(--color-primary);
  background: transparent;
  font-weight: 700;
}

.shell__logout:hover {
  background: var(--color-surface-muted);
}

.shell__main {
  padding: 48px 0 72px;
}

@media (max-width: 640px) {
  .shell__bar,
  .shell__main {
    width: min(100% - 32px, var(--content-width));
  }
}
</style>
