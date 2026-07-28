<template>
  <fieldset class="type-selector">
    <legend>礼物类型</legend>
    <p>{{ locked ? "编辑已有礼物时类型不可更改。" : "先确认记录对象，后续只显示对应的专属字段。" }}</p>
    <div class="type-selector__choices">
      <button
        type="button"
        data-type="product"
        :aria-pressed="modelValue === 'product'"
        :disabled="locked && modelValue !== 'product'"
        @click="$emit('select', 'product')"
      >商品</button>
      <button
        type="button"
        data-type="activity"
        :aria-pressed="modelValue === 'activity'"
        :disabled="locked && modelValue !== 'activity'"
        @click="$emit('select', 'activity')"
      >活动</button>
    </div>
  </fieldset>
</template>

<script setup lang="ts">
import type { GiftTypeCode } from "../../api/gifts";

defineProps<{ modelValue: GiftTypeCode; locked?: boolean }>();
defineEmits<{ select: [type: GiftTypeCode] }>();
</script>

<style scoped>
.type-selector { padding: 0; border: 0; }
legend { color: var(--color-ink); font-weight: 800; }
p { margin: 6px 0 14px; color: var(--color-ink-muted); font-size: .875rem; }
.type-selector__choices { display: flex; gap: 10px; }
button { min-height: 42px; padding: 0 18px; border: 1px solid var(--color-border); border-radius: var(--radius-sm); color: var(--color-ink); background: var(--color-surface); font-weight: 700; }
button[aria-pressed="true"] { border-color: var(--color-primary); color: white; background: var(--color-primary); }
button:disabled { cursor: not-allowed; opacity: .55; }
</style>
