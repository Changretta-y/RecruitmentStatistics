<script setup lang="ts">
import { APPLICATION_STATUS_LABELS, type ApplicationPosition } from "../types/application";
defineProps<{ position: ApplicationPosition }>();
function displayTime(value: string | null): string {
  if (!value) return "未安排";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const pad = (part: number) => String(part).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}
function safeLink(value: string): string | undefined {
  try { const url = new URL(value); return ["https:", "http:"].includes(url.protocol) ? url.href : undefined; }
  catch { return undefined; }
}
</script>

<template>
  <article class="position-flow" :aria-label="`${position.positionName}投递记录`">
    <header class="position-heading"><h3>{{ position.positionName }}</h3><span class="position-status">{{ APPLICATION_STATUS_LABELS[position.currentStage] }}</span></header>
    <p class="position-meta">投递时间：{{ displayTime(position.applicationTime) }}</p>
    <a v-if="safeLink(position.applicationUrl)" :href="safeLink(position.applicationUrl)" target="_blank" rel="noopener noreferrer" class="position-link">查看投递链接</a>
    <p v-if="position.notes" class="position-notes">备注：{{ position.notes }}</p>
    <h4 class="flow-title">面试流程</h4>
    <ul v-if="position.interviews.length" class="interview-list">
      <li v-for="(interview, index) in position.interviews" :key="interview.id ?? index">
        <span class="interview-name">{{ interview.name }}</span>
        <time :datetime="interview.scheduledAt ?? undefined">{{ displayTime(interview.scheduledAt) }}</time>
        <span class="interview-duration">{{ interview.durationMinutes ? `${interview.durationMinutes} 分钟` : '时长未设置' }}</span>
      </li>
    </ul>
    <p v-else class="position-meta">暂无面试环节。</p>
  </article>
</template>

<style scoped>
.position-flow { border: 1px solid #dce3f2; border-radius: 12px; padding: 18px; background: #fff; min-width: 0; overflow-wrap: anywhere; white-space: normal; }
.position-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.position-heading h3 { margin: 0; font-size: 1rem; color: #24375c; }
.position-status { flex-shrink: 0; color: #3157d5; background: #eef3ff; padding: 2px 8px; border-radius: 6px; font-size: .8rem; }
.position-meta, .position-notes { margin: 10px 0; color: #667085; font-size: .85rem; }
.position-notes { white-space: pre-wrap; }
.position-link { color: #3157d5; font-size: .85rem; }
.flow-title { margin: 16px 0 8px; font-size: .85rem; color: #475467; }
.interview-list { list-style: none; padding: 0; margin: 0; }
.interview-list li { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 4px 12px; padding: 10px 0; border-top: 1px solid #eef0f5; font-size: .85rem; }
.interview-name { font-weight: 600; color: #344054; }
.interview-duration { color: #667085; grid-column: 1 / -1; }
@media (max-width: 700px) {
  .position-flow { padding: 14px; }
  .interview-list li { grid-template-columns: minmax(0, 1fr); }
}
</style>
