<script setup lang="ts">
import { computed, ref } from "vue";
import { VTextField } from "vuetify/components/VTextField";

defineOptions({ inheritAttrs: false });

const props = defineProps<{
  modelValue: string | null;
}>();

const emit = defineEmits<{
  (event: "update:modelValue", value: string): void;
}>();

const picker = ref<HTMLInputElement | null>(null);
const displayValue = computed({
  get: () => props.modelValue ?? "",
  set: (value: string) => emit("update:modelValue", value),
});

function toPickerValue(value: string | null): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const pad = (part: number) => String(part).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function openPicker(): void {
  const input = picker.value;
  if (!input) return;
  input.value = toPickerValue(props.modelValue);
  if (typeof input.showPicker === "function") input.showPicker();
  else input.click();
}

function updateFromPicker(event: Event): void {
  emit("update:modelValue", (event.target as HTMLInputElement).value);
}
</script>

<template>
  <div class="date-time-field">
    <VTextField
      v-bind="$attrs"
      v-model="displayValue"
      type="text"
      append-inner-icon="mdi-calendar-clock"
      @click:append-inner="openPicker"
    />
    <input
      ref="picker"
      class="native-date-picker"
      type="datetime-local"
      step="60"
      tabindex="-1"
      aria-hidden="true"
      @input="updateFromPicker"
    />
  </div>
</template>

<style scoped>
.date-time-field { position: relative; }
.native-date-picker {
  position: absolute;
  width: 1px;
  height: 1px;
  opacity: 0;
  pointer-events: none;
}
</style>
