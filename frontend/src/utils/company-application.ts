import type { ApplicationInterview, ApplicationPosition, SharedApplicationStage, SharedStageType } from "../types/application";

export const SHARED_STAGES: Array<{ type: SharedStageType; title: string; field: string }> = [
  { type: "ai_interview", title: "AI 面", field: "aiInterview" },
  { type: "assessment", title: "测评", field: "assessment" },
  { type: "written_test", title: "笔试", field: "writtenTest" },
];
export const LEGACY_INTERVIEWS = [
  { field: "firstInterview", name: "一面" }, { field: "secondInterview", name: "二面" },
  { field: "thirdInterview", name: "三面" }, { field: "hrInterview", name: "HR 面" },
];

export function applicationValue(source: Record<string, unknown>, key: string): unknown {
  const snake = key.replace(/[A-Z]/g, letter => `_${letter.toLowerCase()}`);
  return Object.prototype.hasOwnProperty.call(source, key) ? source[key] : source[snake];
}

export function readInterview(source: Record<string, unknown>): ApplicationInterview {
  return {
    ...(typeof source.id === "number" ? { id: source.id } : {}),
    name: String(source.name ?? ""),
    scheduledAt: applicationValue(source, "scheduledAt") as string | null ?? null,
    durationMinutes: applicationValue(source, "durationMinutes") as number | null ?? null,
  };
}

export function readPositions(source: Record<string, unknown>): ApplicationPosition[] {
  const positions = applicationValue(source, "positions");
  const values = Array.isArray(positions) ? positions : [source];
  return values.map(raw => {
    const position = raw as Record<string, unknown>;
    const interviews = position.interviews;
    return {
      ...(Array.isArray(positions) && typeof position.id === "number" ? { id: position.id } : {}),
      positionName: String(applicationValue(position, "positionName") ?? ""),
      applicationUrl: String(applicationValue(position, "applicationUrl") ?? ""),
      applicationStatus: (applicationValue(position, "applicationStatus") ?? "applied") as ApplicationPosition["applicationStatus"],
      applicationTime: applicationValue(position, "applicationTime") as string | null ?? null,
      notes: String(position.notes ?? ""),
      interviews: Array.isArray(interviews) ? interviews.map(item => readInterview(item as Record<string, unknown>)) : LEGACY_INTERVIEWS.flatMap(stage => {
        const scheduledAt = applicationValue(position, `${stage.field}Time`) as string | null;
        return scheduledAt ? [{ name: stage.name, scheduledAt, durationMinutes: applicationValue(position, `${stage.field}DurationMinutes`) as number | null ?? 60 }] : [];
      }),
    };
  });
}

export function readSharedStages(source: Record<string, unknown>): SharedApplicationStage[] {
  const stages = applicationValue(source, "sharedStages");
  return SHARED_STAGES.map(stage => {
    const raw = Array.isArray(stages) ? stages.find(item => item.type === stage.type) : undefined;
    const interview = raw ? readInterview(raw) : undefined;
    return interview ? { type: stage.type, scheduledAt: interview.scheduledAt, durationMinutes: interview.durationMinutes } : {
      type: stage.type,
      scheduledAt: applicationValue(source, `${stage.field}Time`) as string | null ?? null,
      durationMinutes: applicationValue(source, `${stage.field}DurationMinutes`) as number | null ?? null,
    };
  });
}
