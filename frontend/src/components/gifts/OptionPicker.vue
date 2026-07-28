<template>
  <fieldset class="picker"><legend>{{ label }} <small>可多选</small></legend><div class="options"><button v-for="option in options" :key="option" type="button" :class="{ selected: selected.includes(option) }" @click="$emit('toggle', field, option)">{{ option }}</button></div><input v-bind="attrs" :placeholder="'补充其他' + label + '（可选）'" @change="addCustom" /></fieldset>
</template>

<script setup lang="ts">
defineOptions({ inheritAttrs: false });
import { useAttrs } from "vue";
const attrs = useAttrs();
const props = defineProps<{ label: string; field: string; options: string[]; selected: string[] }>();
const emit = defineEmits<{ toggle: [field: string, value: string] }>();
function addCustom(event: Event) { const value = (event.target as HTMLInputElement).value.trim(); if (value) emit("toggle", props.field, value); (event.target as HTMLInputElement).value = ""; }
</script>

<style scoped>
.picker { display: grid; gap: 8px; padding: 0; border: 0; }.picker legend { padding: 0; color: var(--color-ink-muted); font-size: .875rem; font-weight: 700; }.picker small { color: var(--color-ink-faint); font-weight: 500; }.options { display: flex; flex-wrap: wrap; gap: 8px; }.options button { padding: 8px 12px; border: 1px solid var(--color-border); border-radius: 999px; color: var(--color-ink-muted); background: var(--color-surface); cursor: pointer; }.options button.selected { border-color: var(--color-primary); color: white; background: var(--color-primary); }.picker input { width: 100%; padding: 9px 12px; border: 1px solid var(--color-border); border-radius: var(--radius-sm); color: var(--color-ink); background: var(--color-surface); }
</style>
