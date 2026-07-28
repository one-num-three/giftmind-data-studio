<template>
  <section class="tools"><div class="heading"><div><p>数据维护</p><h1>数据工具</h1><span>把重复录入交给选择、AI 和批量工具。</span></div></div>
    <p v-if="notice" class="notice" role="status">{{ notice }}</p>
    <div class="grid"><section class="card"><h2>DeepSeek 密钥</h2><p>密钥只写入服务器 <code>.env</code>，不会显示、下载或保存到浏览器。</p><input data-field="deepseek-key" v-model="deepSeekKey" type="password" autocomplete="new-password" placeholder="粘贴 DeepSeek API Key" /><button data-action="save-deepseek-key" type="button" :disabled="!deepSeekKey.trim()" @click="saveKey">保存密钥</button><small>{{ keyStatus }}</small></section>
      <section class="card"><h2>DeepSeek 预判</h2><p>输入一个礼物名称，先查看模型建议，再回到录入页确认。</p><input v-model="aiName" placeholder="例如：南京博物院文创书签" /><select v-model="aiType"><option value="product">商品</option><option value="activity">活动</option></select><button type="button" @click="runAI">开始预判</button><pre v-if="aiResult">{{ JSON.stringify(aiResult, null, 2) }}</pre></section>
      <section class="card"><h2>自定义字段</h2><p>字段先定义一次，后续采集同学就能按统一格式填写。</p><div class="row"><input v-model="field.machineKey" placeholder="machine_key，如 eco_score" /><input v-model="field.displayName" placeholder="显示名称" /></div><select v-model="field.valueType"><option value="text">文本</option><option value="number">数字</option><option value="boolean">是/否</option><option value="select">选项</option></select><button type="button" @click="addField">添加字段</button><ul><li v-for="item in fields" :key="item.id">{{ item.displayName }} <small>{{ item.machineKey }} · {{ item.valueType }}</small></li></ul></section>
      <section class="card"><h2>批量导入 / 导出</h2><p>Excel 第一行使用：name、type、status、description、price_min、price_max、tags。</p><button type="button" @click="download('/api/export/xlsx', 'giftmind-gifts.xlsx')">导出 Excel</button><label class="file">选择 Excel 导入<input type="file" accept=".xlsx" @change="importExcel" /></label><label class="file">恢复备份<input type="file" accept=".zip" @change="restoreBackup" /></label><button type="button" @click="download('/api/backup', 'giftmind-backup.zip')">下载备份</button></section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import type { GiftTypeCode } from "../api/gifts";
import { createCustomField, deepSeekStatus, downloadBlob, listCustomFields, saveDeepSeekKey, suggestGift, uploadFile } from "../api/tools";
const notice = ref(""); const fields = ref<Awaited<ReturnType<typeof listCustomFields>>>([]); const aiName = ref(""); const aiType = ref<GiftTypeCode>("product"); const aiResult = ref<unknown>(null); const deepSeekKey = ref(""); const keyStatus = ref("检查中…"); const field = reactive({ machineKey: "", displayName: "", valueType: "text" });
async function loadFields() { fields.value = await listCustomFields(); }
async function saveKey() { if (!deepSeekKey.value.trim()) return; const result = await saveDeepSeekKey(deepSeekKey.value.trim()); deepSeekKey.value = ""; keyStatus.value = `已配置 ${result.model}`; notice.value = "DeepSeek 密钥已写入服务器 .env。"; }
async function runAI() { if (!aiName.value.trim()) return; aiResult.value = await suggestGift(aiName.value, aiType.value); }
async function addField() { if (!field.machineKey || !field.displayName) return; await createCustomField({ machineKey: field.machineKey, displayName: field.displayName, valueType: field.valueType, cardinality: "single" }); notice.value = "自定义字段已添加。"; field.machineKey = ""; field.displayName = ""; await loadFields(); }
async function download(path: string, name: string) { const blob = await downloadBlob(path); const url = URL.createObjectURL(blob); const anchor = document.createElement("a"); anchor.href = url; anchor.download = name; anchor.click(); URL.revokeObjectURL(url); }
async function importExcel(event: Event) { const file = (event.target as HTMLInputElement).files?.[0]; if (file) { const result = await uploadFile("/api/import/xlsx", file); notice.value = `导入完成：${result.imported ?? 0} 条。`; } }
async function restoreBackup(event: Event) { const file = (event.target as HTMLInputElement).files?.[0]; if (file) { const result = await uploadFile("/api/restore", file); notice.value = `恢复完成：${result.restored ?? 0} 条。`; } }
onMounted(async () => {
  try { await loadFields(); } catch { notice.value = "字段列表暂时无法加载，其他工具仍可使用。"; }
  try { const result = await deepSeekStatus(); keyStatus.value = result.configured ? `已配置 ${result.model}` : "尚未配置"; } catch { keyStatus.value = "暂时无法读取状态"; }
});
</script>

<style scoped>
.tools { display: grid; gap: 20px; }.heading p { margin: 0 0 6px; color: var(--color-accent); font-size: .8rem; font-weight: 800; }.heading h1 { margin: 0 0 8px; color: var(--color-ink); }.heading span, .card p { color: var(--color-ink-muted); }.notice { padding: 10px 12px; border-radius: var(--radius-sm); color: var(--color-primary); background: #e7f3e9; }.grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }.card { display: grid; align-content: start; gap: 12px; padding: 20px; border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-surface); }.card h2 { margin: 0; color: var(--color-ink); font-size: 1.1rem; }.card input, .card select { min-height: 40px; padding: 0 10px; border: 1px solid var(--color-border); border-radius: var(--radius-sm); }.card button { min-height: 40px; padding: 0 12px; border: 0; border-radius: var(--radius-sm); color: white; background: var(--color-primary); font-weight: 800; }.row { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }.file { display: grid; gap: 6px; color: var(--color-primary); font-weight: 700; }.file input { padding: 8px; }.card ul { margin: 0; padding-left: 18px; color: var(--color-ink); }.card small { color: var(--color-ink-muted); }pre { overflow: auto; padding: 10px; border-radius: var(--radius-sm); background: var(--color-surface-muted); }@media (max-width: 900px) { .grid { grid-template-columns: 1fr; } }
</style>
