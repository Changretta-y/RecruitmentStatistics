<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink, useRoute } from "vue-router";
import { watch } from "vue";
import { VBtn } from "vuetify/components/VBtn";
import { VContainer } from "vuetify/components/VGrid";

import AppShell from "../components/AppShell.vue";
import { getCalendarEvents, type CalendarEvent } from "../api/calendar";

type ViewMode = "month" | "week";
interface EventFragment { event: CalendarEvent; startMinute: number; endMinute: number; }

const SHANGHAI_OFFSET_MS = 8 * 60 * 60 * 1000;
const stageLabels: Record<string, string> = {
  ai_interview: "AI 面试",
  written_test: "笔试",
  first_interview: "一面",
  second_interview: "二面",
  third_interview: "三面",
  hr_interview: "HR 面",
};

function pad(value: number): string { return String(value).padStart(2, "0"); }
function dateKey(year: number, month: number, day: number): string {
  return `${year}-${pad(month)}-${pad(day)}`;
}
function keyToUtcDate(key: string): Date {
  const [year, month, day] = key.split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, day));
}
function shiftDate(key: string, amount: number): string {
  const date = keyToUtcDate(key);
  date.setUTCDate(date.getUTCDate() + amount);
  return dateKey(date.getUTCFullYear(), date.getUTCMonth() + 1, date.getUTCDate());
}
function beijingToday(): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Shanghai", year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(new Date());
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return dateKey(Number(values.year), Number(values.month), Number(values.day));
}
function mondayOf(key: string): string {
  const date = keyToUtcDate(key);
  const weekday = date.getUTCDay();
  return shiftDate(key, -((weekday + 6) % 7));
}
function monthRange(anchor: string): { start: string; end: string; dates: string[] } {
  const [year, month] = anchor.split("-").map(Number);
  const first = dateKey(year, month, 1);
  const last = dateKey(year, month, new Date(Date.UTC(year, month, 0)).getUTCDate());
  const start = mondayOf(first);
  const lastWeekday = keyToUtcDate(last).getUTCDay();
  const end = shiftDate(last, 8 - lastWeekday);
  const dates: string[] = [];
  for (let cursor = start; cursor < end; cursor = shiftDate(cursor, 1)) dates.push(cursor);
  return { start, end, dates };
}
function weekRange(anchor: string): { start: string; end: string; dates: string[] } {
  const start = mondayOf(anchor);
  const dates = Array.from({ length: 7 }, (_, index) => shiftDate(start, index));
  return { start, end: shiftDate(start, 7), dates };
}
function formatClock(value: string): string {
  const local = new Date(Date.parse(value) + SHANGHAI_OFFSET_MS);
  return `${pad(local.getUTCHours())}:${pad(local.getUTCMinutes())}`;
}
function beijingDate(value: string): string {
  const local = new Date(Date.parse(value) + SHANGHAI_OFFSET_MS);
  return dateKey(local.getUTCFullYear(), local.getUTCMonth() + 1, local.getUTCDate());
}
function formatDateLabel(key: string): string {
  const date = keyToUtcDate(key);
  return `${date.getUTCMonth() + 1}月${date.getUTCDate()}日`;
}

const mode = ref<ViewMode>("month");
const route = useRoute();
const anchorDate = ref(beijingToday());
const events = ref<CalendarEvent[]>([]);
const loading = ref(false);
const loadError = ref("");
const selectedEvent = ref<CalendarEvent | null>(null);
const expandedDate = ref("");
let requestVersion = 0;

const range = computed(() => mode.value === "month" ? monthRange(anchorDate.value) : weekRange(anchorDate.value));
const visibleHeading = computed(() => {
  const [year, month] = anchorDate.value.split("-").map(Number);
  return mode.value === "month"
    ? `${year}年${month}月`
    : `${range.value.start} 至 ${shiftDate(range.value.end, -1)}`;
});
const weekdayLabels = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"];

function minutesOnDate(value: string): number {
  const local = new Date(Date.parse(value) + SHANGHAI_OFFSET_MS);
  return local.getUTCHours() * 60 + local.getUTCMinutes() + local.getUTCSeconds() / 60;
}
function fragmentsForDate(key: string): EventFragment[] {
  const dayStart = keyToUtcDate(key).getTime() - SHANGHAI_OFFSET_MS;
  const dayEnd = dayStart + 24 * 60 * 60 * 1000;
  return events.value.flatMap((event) => {
    const start = Date.parse(event.start_at);
    const end = Date.parse(event.end_at);
    const clippedStart = Math.max(start, dayStart);
    const clippedEnd = Math.min(end, dayEnd);
    if (clippedStart >= clippedEnd) return [];
    const localStart = new Date(clippedStart + SHANGHAI_OFFSET_MS);
    const localEnd = new Date(clippedEnd + SHANGHAI_OFFSET_MS);
    const startMinute = localStart.getUTCHours() * 60 + localStart.getUTCMinutes() + localStart.getUTCSeconds() / 60;
    let endMinute = localEnd.getUTCHours() * 60 + localEnd.getUTCMinutes() + localEnd.getUTCSeconds() / 60;
    if (clippedEnd === dayEnd) endMinute = 1440;
    return [{ event, startMinute, endMinute }];
  });
}
function dayEvents(key: string): CalendarEvent[] {
  return fragmentsForDate(key).map((fragment) => fragment.event);
}
function eventClockForDate(event: CalendarEvent, key: string): string {
  const fragment = fragmentsForDate(key).find((item) => item.event === event);
  return fragment ? `${pad(Math.floor(fragment.startMinute / 60))}:${pad(Math.floor(fragment.startMinute % 60))}` : formatClock(event.start_at);
}
function eventEndClockForDate(event: CalendarEvent, key: string): string {
  const fragment = fragmentsForDate(key).find((item) => item.event === event);
  if (!fragment) return formatClock(event.end_at);
  if (fragment.endMinute === 1440) return "24:00";
  return `${pad(Math.floor(fragment.endMinute / 60))}:${pad(Math.floor(fragment.endMinute % 60))}`;
}
function fragmentStyle(fragment: EventFragment, key: string, index: number): Record<string, string> {
  const top = fragment.startMinute / 1440 * 100;
  const height = Math.max((fragment.endMinute - fragment.startMinute) / 1440 * 100, 0.28);
  // Give overlapping events separate narrow lanes while retaining every independent button.
  const peers = fragmentsForDate(key).filter((other) =>
    other.startMinute < fragment.endMinute && fragment.startMinute < other.endMinute,
  );
  const laneCount = Math.max(peers.length, 1);
  const lane = laneCount > 1 ? peers.findIndex((peer) => peer.event === fragment.event) : 0;
  return {
    top: `${top}%`, height: `${height}%`, left: `${lane * 100 / laneCount}%`,
    width: `${100 / laneCount}%`,
    "--event-lane": String(index),
  };
}
function stageLabel(event: CalendarEvent): string { return stageLabels[event.stage] ?? event.stage; }
function eventAriaLabel(event: CalendarEvent, key: string): string {
  const continuation = beijingDate(event.start_at) < key ? "（前一日开始，续接）" : "";
  const sameCompanyEvents = dayEvents(key)
    .filter((other) => other.company_name === event.company_name && other !== event)
    .map((other) => `${stageLabel(other)} ${eventClockForDate(other, key)}`);
  const related = sameCompanyEvents.length ? `；同公司其他安排：${sameCompanyEvents.join("、")}` : "";
  return `${event.company_name} ${event.position_name} ${stageLabel(event)} ${eventClockForDate(event, key)} ${continuation}${related}`.trim();
}
function isWrittenTest(event: CalendarEvent): boolean { return event.stage === "written_test"; }

async function loadEvents(): Promise<void> {
  const version = ++requestVersion;
  const requestedRange = { start: range.value.start, end: range.value.end };
  loading.value = true;
  loadError.value = "";
  events.value = [];
  try {
    const response = await getCalendarEvents(requestedRange.start, requestedRange.end);
    if (version !== requestVersion) return;
    events.value = Array.isArray(response.events) ? response.events : [];
  } catch {
    if (version !== requestVersion) return;
    loadError.value = "日历加载失败，请检查网络后重试。";
  } finally {
    if (version === requestVersion) loading.value = false;
  }
}
function changeMode(next: ViewMode): void {
  if (mode.value === next) return;
  mode.value = next;
  void loadEvents();
}
function movePeriod(amount: number): void {
  if (mode.value === "week") anchorDate.value = shiftDate(anchorDate.value, amount * 7);
  else {
    const [year, month, day] = anchorDate.value.split("-").map(Number);
    const targetMonth = new Date(Date.UTC(year, month - 1 + amount, 1));
    const lastDay = new Date(Date.UTC(targetMonth.getUTCFullYear(), targetMonth.getUTCMonth() + 1, 0)).getUTCDate();
    anchorDate.value = dateKey(targetMonth.getUTCFullYear(), targetMonth.getUTCMonth() + 1, Math.min(day, lastDay));
  }
  void loadEvents();
}
function goToday(): void {
  anchorDate.value = beijingToday();
  void loadEvents();
}
function editApplication(event: CalendarEvent): string {
  return `/applications/${event.application_id}/edit`;
}
function isInAnchorMonth(key: string): boolean {
  return key.slice(0, 7) === anchorDate.value.slice(0, 7);
}
function dayNumber(key: string): number { return Number(key.slice(-2)); }

watch(() => route.fullPath, () => { void loadEvents(); });
onMounted(() => { void loadEvents(); });
</script>

<template>
  <AppShell title="日历">
  <VContainer class="calendar-page py-6 py-md-8" fluid>
    <header class="calendar-header">
      <div>
        <p class="eyebrow">我的日程</p>
        <h1 class="calendar-title">日历</h1>
        <p class="timezone-label">北京时间（Asia/Shanghai）</p>
      </div>
      <div class="calendar-controls" aria-label="日历控制">
        <div class="mode-controls" aria-label="视图切换">
          <VBtn :variant="mode === 'week' ? 'flat' : 'tonal'" :color="mode === 'week' ? 'primary' : undefined" aria-label="周视图" @click="changeMode('week')">周</VBtn>
          <VBtn :variant="mode === 'month' ? 'flat' : 'tonal'" :color="mode === 'month' ? 'primary' : undefined" aria-label="月视图" @click="changeMode('month')">月</VBtn>
        </div>
        <div class="period-controls">
          <VBtn variant="tonal" aria-label="上一周期" @click="movePeriod(-1)">‹</VBtn>
          <VBtn variant="text" aria-label="今天" @click="goToday">今天</VBtn>
          <VBtn variant="tonal" aria-label="下一周期" @click="movePeriod(1)">›</VBtn>
        </div>
      </div>
    </header>

    <div class="period-heading" aria-live="polite">
      <h2>{{ visibleHeading }}</h2>
      <span v-if="mode === 'month'">完整周视图 · 周一至周日</span>
    </div>

    <div v-if="loading" class="calendar-status" role="status">正在加载日历安排…</div>
    <div v-if="loadError" class="calendar-error" role="alert">
      <span>{{ loadError }}</span>
      <VBtn variant="tonal" color="primary" aria-label="重试加载日历" @click="loadEvents">重试</VBtn>
    </div>

    <div class="weekday-heading" :class="`weekday-${mode}`" aria-hidden="true">
      <span v-for="weekday in weekdayLabels" :key="weekday">{{ weekday }}</span>
    </div>
    <section class="calendar-grid" :class="`calendar-grid-${mode}`" aria-label="日历安排">
      <article
        v-for="(key, dayIndex) in range.dates"
        :key="key"
        class="day-cell"
        :class="[{ 'outside-month': mode === 'month' && !isInAnchorMonth(key), 'is-today': key === beijingToday() }, `day-cell-${mode}`]"
        :data-date="key"
      >
        <header class="day-heading">
          <span class="day-number">{{ dayNumber(key) }}</span>
          <span v-if="key === beijingToday()" class="today-marker">今天</span>
          <span class="day-count">{{ dayEvents(key).length ? `${dayEvents(key).length} 项` : "无安排" }}</span>
        </header>
        <div class="day-timeline" :class="`timeline-${mode}`" :aria-label="`${key} 从 00:00 到 24:00 的日程时间轴`">
          <div v-for="hour in [0, 6, 12, 18, 24]" :key="hour" class="time-tick" :style="{ top: `${hour / 24 * 100}%` }">
            <span>{{ pad(hour) }}:00</span>
          </div>
          <template v-for="(fragment, eventIndex) in fragmentsForDate(key)" :key="`${fragment.event.application_id}-${fragment.event.stage}`">
            <button
              v-if="mode === 'week' || eventIndex < 5 || expandedDate === key"
              type="button"
              class="calendar-event"
              :class="{ 'written-test': isWrittenTest(fragment.event), interview: !isWrittenTest(fragment.event) }"
              :style="fragmentStyle(fragment, key, eventIndex)"
              :aria-label="eventAriaLabel(fragment.event, key)"
              :title="eventAriaLabel(fragment.event, key)"
              @click="selectedEvent = fragment.event"
              @keydown.enter.prevent="selectedEvent = fragment.event"
            >
              <span class="event-symbol" aria-hidden="true">{{ isWrittenTest(fragment.event) ? "▧" : "●" }}</span>
              <span class="event-clock">{{ eventClockForDate(fragment.event, key) }}</span>
              <span class="event-end-clock">–{{ eventEndClockForDate(fragment.event, key) }}</span>
              <span class="event-duration">{{ fragment.event.duration_minutes }} 分钟</span>
              <span class="event-name">{{ fragment.event.company_name }}</span>
              <span class="event-stage">{{ stageLabel(fragment.event) }}</span>
              <span v-if="beijingDate(fragment.event.start_at) < key" class="continuation-mark">前日续</span>
              <span v-if="beijingDate(fragment.event.end_at) > key" class="continuation-mark">次日续接</span>
            </button>
          </template>
          <button
            v-if="mode === 'month' && dayEvents(key).length > 5 && expandedDate !== key"
            type="button"
            class="more-events"
            :aria-label="`更多 ${key} 全部安排 ${dayEvents(key).length} 项`"
            @click="expandedDate = key"
          >查看全部安排（{{ dayEvents(key).length }} 项）</button>
          <span v-if="dayEvents(key).length === 0 && !loading && !loadError" class="empty-day">暂无安排</span>
        </div>
      </article>
    </section>

    <footer class="calendar-legend" aria-label="安排类型说明">
      <span><b class="legend-symbol written">▧</b> 笔试</span>
      <span><b class="legend-symbol interview">●</b> 面试</span>
      <span>事件可点击或按 Enter 打开详情</span>
    </footer>

    <div v-if="selectedEvent" class="dialog-backdrop" @click.self="selectedEvent = null">
      <section class="event-dialog" role="dialog" aria-modal="true" aria-labelledby="event-dialog-title">
        <button type="button" class="dialog-close" aria-label="关闭安排详情" @click="selectedEvent = null">×</button>
        <p class="eyebrow">{{ stageLabel(selectedEvent) }}</p>
        <h2 id="event-dialog-title">{{ selectedEvent.company_name }}</h2>
        <p class="event-position">{{ selectedEvent.position_name }}</p>
        <dl class="event-details">
          <div><dt>阶段</dt><dd>{{ stageLabel(selectedEvent) }}</dd></div>
          <div><dt>开始时间</dt><dd>{{ beijingDate(selectedEvent.start_at) }} {{ formatClock(selectedEvent.start_at) }}</dd></div>
          <div><dt>结束时间</dt><dd>{{ beijingDate(selectedEvent.end_at) }} {{ formatClock(selectedEvent.end_at) }}<span v-if="beijingDate(selectedEvent.end_at) > beijingDate(selectedEvent.start_at)">（次日）</span></dd></div>
          <div><dt>时长</dt><dd>{{ selectedEvent.duration_minutes }} 分钟</dd></div>
          <div><dt>时区</dt><dd>北京时间（Asia/Shanghai）</dd></div>
        </dl>
        <RouterLink class="edit-application" :to="editApplication(selectedEvent)">编辑此投递</RouterLink>
      </section>
    </div>
  </VContainer>
  </AppShell>
</template>

<style scoped>
.calendar-page { max-width: 1680px; color: #182230; }
.calendar-header { display:flex; align-items:center; justify-content:space-between; gap:24px; margin:0 auto 24px; max-width:1500px; }
.eyebrow { margin:0 0 4px; color:#526179; font-size:.78rem; font-weight:700; letter-spacing:.06em; }
.calendar-title { margin:0; font-size:clamp(1.7rem,3vw,2.25rem); line-height:1.2; }
.timezone-label { margin:7px 0 0; color:#526179; font-size:.9rem; }
.calendar-controls,.mode-controls,.period-controls { display:flex; align-items:center; gap:8px; }
.calendar-controls { flex-wrap:wrap; justify-content:flex-end; }
.mode-controls { padding:4px; background:#e8edf7; border-radius:14px; }
.period-heading { max-width:1500px; margin:0 auto 14px; display:flex; align-items:baseline; gap:16px; }
.period-heading h2 { margin:0; font-size:1.22rem; }
.period-heading span { color:#667085; font-size:.85rem; }
.calendar-status,.calendar-error { max-width:1500px; margin:0 auto 12px; padding:10px 14px; border-radius:12px; }
.calendar-status { color:#475467; background:#eef2f8; }
.calendar-error { display:flex; align-items:center; justify-content:space-between; gap:12px; color:#8b1e16; background:#fff0ee; }
.weekday-heading,.calendar-grid { max-width:1500px; margin:0 auto; display:grid; grid-template-columns:repeat(7,minmax(0,1fr)); }
.weekday-heading { text-align:center; color:#667085; font-size:.78rem; font-weight:700; }
.weekday-heading span { padding:8px; }
.calendar-grid { border-left:1px solid #dce2ed; border-top:1px solid #dce2ed; background:white; }
.day-cell { position:relative; min-width:0; border-right:1px solid #dce2ed; border-bottom:1px solid #dce2ed; background:#fff; }
.day-cell.outside-month { background:#f8f9fc; color:#788397; }
.day-cell.is-today { box-shadow:inset 0 0 0 2px #3157d5; z-index:1; }
.day-cell-month { min-height:130px; }
.day-cell-week { min-height:570px; }
.day-heading { min-height:29px; display:flex; align-items:center; gap:5px; padding:4px 7px; font-size:.75rem; }
.day-number { display:inline-grid; place-items:center; width:23px; height:23px; font-weight:700; }
.is-today .day-number { color:white; background:#3157d5; border-radius:50%; }
.today-marker { color:#3157d5; font-weight:700; }
.day-count { margin-left:auto; color:#667085; font-size:.66rem; }
.day-timeline { position:relative; overflow:hidden; isolation:isolate; }
.timeline-month { height:96px; margin:0 4px 4px; border-top:1px solid #eef0f5; }
.timeline-week { height:520px; margin:0 6px 8px 40px; border-left:1px solid #cdd5e2; }
.time-tick { position:absolute; z-index:-1; left:0; right:0; border-top:1px solid #edf0f5; pointer-events:none; }
.time-tick span { position:absolute; top:-8px; left:1px; padding:0 2px; color:#8791a2; background:white; font-size:8px; line-height:1; white-space:nowrap; }
.timeline-week .time-tick span { left:-38px; font-size:.64rem; }
.calendar-event { position:absolute; z-index:2; display:flex; align-items:center; gap:2px; min-height:4px; overflow:hidden; padding:1px 2px; border:1px solid #3157d5; border-radius:3px; color:#12338f; background:#e8efff; font-size:.56rem; line-height:1; text-align:left; cursor:pointer; }
.calendar-event:hover,.calendar-event:focus-visible { z-index:4; outline:2px solid #172e78; outline-offset:1px; }
.calendar-event.written-test { border-style:dashed; border-color:#8a4c00; color:#663800; background:#fff3d6; }
.calendar-event.interview { border-left-width:3px; }
.event-symbol { flex:none; font-size:.58rem; }
.event-clock { flex:none; font-variant-numeric:tabular-nums; }
.event-end-clock,.event-duration { flex:none; font-variant-numeric:tabular-nums; }
.event-name { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.event-stage { display:none; }
.continuation-mark { flex:none; font-weight:700; }
.timeline-week .calendar-event { min-height:12px; gap:5px; padding:3px 4px; border-radius:5px; font-size:.76rem; line-height:1.2; }
.timeline-week .event-stage { display:inline; margin-left:auto; white-space:nowrap; }
.more-events { position:absolute; z-index:5; right:2px; bottom:1px; max-width:100%; padding:1px 4px; border:0; border-radius:3px; color:#243c78; background:#e3eaf8; font-size:.58rem; cursor:pointer; }
.empty-day { position:absolute; top:48%; left:4px; color:#a2aab8; font-size:.56rem; }
.calendar-legend { max-width:1500px; margin:14px auto 0; display:flex; flex-wrap:wrap; gap:18px; color:#667085; font-size:.78rem; }
.legend-symbol { margin-right:4px; }.legend-symbol.written { color:#8a4c00; }.legend-symbol.interview { color:#3157d5; }
.dialog-backdrop { position:fixed; inset:0; z-index:1000; display:grid; place-items:center; padding:20px; background:rgba(16,24,40,.45); }
.event-dialog { position:relative; width:min(100%,520px); padding:28px; border-radius:18px; background:white; box-shadow:0 20px 50px #10182840; }
.event-dialog h2 { margin:0; font-size:1.5rem; }.event-position { margin:5px 0 20px; color:#667085; }
.dialog-close { position:absolute; top:12px; right:14px; border:0; color:#667085; background:none; font-size:1.7rem; cursor:pointer; }
.event-details { margin:0 0 20px; }.event-details div { display:grid; grid-template-columns:100px 1fr; gap:10px; padding:8px 0; border-top:1px solid #eef0f5; }
.event-details dt { color:#667085; }.event-details dd { margin:0; font-variant-numeric:tabular-nums; }
.edit-application { display:inline-flex; align-items:center; min-height:40px; padding:0 16px; border-radius:10px; color:white; background:#3157d5; text-decoration:none; font-weight:700; }
@media(max-width:900px) { .calendar-grid-month,.weekday-month { min-width:760px; }.calendar-page { overflow-x:auto; }.day-cell-month { min-height:115px; } }
@media(max-width:650px) { .calendar-header { align-items:flex-start; flex-direction:column; }.calendar-controls { justify-content:flex-start; }.day-cell-week { min-height:430px; }.timeline-week { height:380px; }.calendar-grid-week,.weekday-week { min-width:900px; }.period-heading { align-items:flex-start; flex-direction:column; gap:2px; } }
</style>
