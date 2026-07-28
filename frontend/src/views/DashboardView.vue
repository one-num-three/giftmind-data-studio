<template>
  <section class="dashboard" aria-labelledby="dashboard-title">
    <div class="dashboard__heading">
      <div>
        <p class="dashboard__eyebrow">资料维护</p>
        <h1 id="dashboard-title">礼物数据</h1>
        <p>从这里开始录入、整理和维护团队礼物资料。</p>
      </div>
    </div>

    <section class="dashboard__empty" aria-labelledby="empty-title">
      <h2 id="empty-title">准备就绪</h2>
      <p>礼物资料库的录入和列表功能将在此工作区中显示。</p>
    </section>
  </section>
</template>

<style scoped>
.dashboard {
  display: grid;
  gap: 32px;
}

.dashboard__heading {
  display: flex;
}

.dashboard__eyebrow {
  margin: 0 0 8px;
  color: var(--color-accent);
  font-size: 0.8125rem;
  font-weight: 800;
  letter-spacing: 0.08em;
}

h1,
h2,
p {
  margin-top: 0;
}

h1 {
  margin-bottom: 10px;
  color: var(--color-ink);
  font-size: clamp(2rem, 4vw, 3rem);
  line-height: 1.1;
}

.dashboard__heading p:not(.dashboard__eyebrow),
.dashboard__empty p {
  margin-bottom: 0;
  color: var(--color-ink-muted);
  line-height: 1.6;
}

.dashboard__empty {
  max-width: 720px;
  padding: 32px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
}

h2 {
  margin-bottom: 8px;
  color: var(--color-ink);
  font-size: 1.125rem;
}

</style>
