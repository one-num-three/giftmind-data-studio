<template>
  <nav class="progress" aria-label="录入进度">
    <ol>
      <li v-for="section in sections" :key="section" :class="{ 'progress__item--current': section === current }">
        {{ section }}
      </li>
    </ol>
  </nav>
</template>

<script setup lang="ts">
defineProps<{ sections: string[]; current: string }>();
</script>

<style scoped>
.progress { padding: 18px; border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-surface); }
ol { display: grid; gap: 12px; margin: 0; padding: 0; list-style: none; color: var(--color-ink-muted); font-size: .875rem; }
li::before { display: inline-grid; width: 22px; height: 22px; place-items: center; margin-right: 9px; border-radius: 50%; background: var(--color-surface-muted); content: counter(list-item); }
.progress__item--current { color: var(--color-primary); font-weight: 800; }
.progress__item--current::before { color: white; background: var(--color-primary); }
@media (max-width: 820px) { ol { grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; } }
</style>
