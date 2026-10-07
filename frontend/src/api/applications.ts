import { apiClient, type AuthRequestConfig } from "./http";
import {
  type ApplicationPage,
  type ApplicationQuery,
  type JobApplication,
} from "../types/application";
import { parseApplicationQuery } from "../utils/application-query";
import { readInterview, readPositions, readSharedStages } from "../utils/company-application";

const applicationFieldMap: Record<string, string> = {
  companyName: "company_name",
  positionName: "position_name",
  applicationUrl: "application_url",
  applicationStatus: "application_status",
  currentStage: "current_stage",
  applicationTime: "application_time",
  aiInterviewTime: "ai_interview_time",
  aiInterviewDurationMinutes: "ai_interview_duration_minutes",
  writtenTestTime: "written_test_time",
  writtenTestDurationMinutes: "written_test_duration_minutes",
  firstInterviewTime: "first_interview_time",
  firstInterviewDurationMinutes: "first_interview_duration_minutes",
  secondInterviewTime: "second_interview_time",
  secondInterviewDurationMinutes: "second_interview_duration_minutes",
  thirdInterviewTime: "third_interview_time",
  thirdInterviewDurationMinutes: "third_interview_duration_minutes",
  hrInterviewTime: "hr_interview_time",
  hrInterviewDurationMinutes: "hr_interview_duration_minutes",
  createdAt: "created_at",
  updatedAt: "updated_at",
};

function mapApplication(value: Record<string, unknown>): JobApplication {
  const get = (snake: string, camel: string): unknown => value[snake] ?? value[camel];
  const rawCompany = get("company", "company");
  const companyValue = rawCompany && typeof rawCompany === "object" ? rawCompany as Record<string, unknown> : {};
  const companyId = Number(get("company_id", "companyId") ?? companyValue.id ?? 0);
  const companyName = String(get("company_name", "companyName") ?? companyValue.company_name ?? companyValue.companyName ?? "");
  const recruitmentUrl = (get("recruitment_url", "recruitmentUrl") ?? companyValue.recruitment_url ?? companyValue.recruitmentUrl ?? null) as string | null;
  return {
    id: value.id as number,
    user: value.user as number,
    companyId,
    company: { id: companyId, companyName, recruitmentUrl },
    companyName,
    recruitmentUrl,
    positionName: get("position_name", "positionName") as string,
    applicationUrl: (get("application_url", "applicationUrl") as string) ?? "",
    applicationStatus: get("application_status", "applicationStatus") as JobApplication["applicationStatus"],
    currentStage: (get("current_stage", "currentStage") as JobApplication["currentStage"]) ?? null,
    applicationTime: (get("application_time", "applicationTime") as string | null) ?? null,
    aiInterviewTime: (get("ai_interview_time", "aiInterviewTime") as string | null) ?? null,
    aiInterviewDurationMinutes: (get("ai_interview_duration_minutes", "aiInterviewDurationMinutes") as number | null) ?? null,
    writtenTestTime: (get("written_test_time", "writtenTestTime") as string | null) ?? null,
    writtenTestDurationMinutes: (get("written_test_duration_minutes", "writtenTestDurationMinutes") as number | null) ?? null,
    firstInterviewTime: (get("first_interview_time", "firstInterviewTime") as string | null) ?? null,
    firstInterviewDurationMinutes: (get("first_interview_duration_minutes", "firstInterviewDurationMinutes") as number | null) ?? null,
    secondInterviewTime: (get("second_interview_time", "secondInterviewTime") as string | null) ?? null,
    secondInterviewDurationMinutes: (get("second_interview_duration_minutes", "secondInterviewDurationMinutes") as number | null) ?? null,
    thirdInterviewTime: (get("third_interview_time", "thirdInterviewTime") as string | null) ?? null,
    thirdInterviewDurationMinutes: (get("third_interview_duration_minutes", "thirdInterviewDurationMinutes") as number | null) ?? null,
    hrInterviewTime: (get("hr_interview_time", "hrInterviewTime") as string | null) ?? null,
    hrInterviewDurationMinutes: (get("hr_interview_duration_minutes", "hrInterviewDurationMinutes") as number | null) ?? null,
    notes: (get("notes", "notes") as string) ?? "",
    createdAt: get("created_at", "createdAt") as string,
    updatedAt: get("updated_at", "updatedAt") as string,
    positions: readPositions(value),
    sharedStages: readSharedStages(value),
  };
}

function mapPage(value: Record<string, unknown>): ApplicationPage {
  const body =
    value.data && typeof value.data === "object" && !Array.isArray(value.data)
      ? (value.data as Record<string, unknown>)
      : value;
  const results = Array.isArray(body.results)
    ? body.results
    : Array.isArray(body.data)
      ? body.data
      : [];
  return {
    count: Number(body.count ?? 0),
    page: Number(body.page ?? 1),
    pageSize: Number(body.page_size ?? body.pageSize ?? 20) as ApplicationPage["pageSize"],
    totalPages: Number(body.total_pages ?? body.totalPages ?? 0),
    next: (body.next as string | null) ?? null,
    previous: (body.previous as string | null) ?? null,
    results: (results as Record<string, unknown>[]).map(mapApplication),
  };
}

function toSnakePayload(payload: Record<string, unknown>, nested = false): Record<string, unknown> {
  const result: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(payload)) {
    if (value === undefined) continue;
    if (!nested && ["id", "user", "createdAt", "updatedAt", "currentStage", "created_at", "updated_at", "current_stage"].includes(key)) {
      continue;
    }
    const mapped = Array.isArray(value) ? value.map(item => item && typeof item === "object" ? toSnakePayload(item as Record<string, unknown>, true) : item)
      : value && typeof value === "object" ? toSnakePayload(value as Record<string, unknown>, true) : value;
    result[applicationFieldMap[key] ?? key.replace(/[A-Z]/g, letter => `_${letter.toLowerCase()}`)] = mapped;
  }
  return result;
}

function apiQuery(query: ApplicationQuery = {}): Record<string, string | number> {
  const normalized = parseApplicationQuery(query as Record<string, unknown>);
  const params: Record<string, string | number> = {
    page: normalized.page,
    page_size: normalized.pageSize,
  };
  if (normalized.search) params.search = normalized.search;
  if (normalized.applicationStatus) {
    const statuses = Array.isArray(normalized.applicationStatus)
      ? normalized.applicationStatus
      : [normalized.applicationStatus];
    if (statuses.length > 0) params.application_status = statuses.join(",");
  }
  if (normalized.applicationTimeAfter) params.application_time_after = normalized.applicationTimeAfter;
  if (normalized.applicationTimeBefore) params.application_time_before = normalized.applicationTimeBefore;
  if (normalized.ordering) params.ordering = normalized.ordering;
  return params;
}

export async function listApplications(query: ApplicationQuery = {}): Promise<ApplicationPage> {
  const response = await apiClient.get("/api/v1/applications/", { params: apiQuery(query) });
  return mapPage(response.data as Record<string, unknown>);
}

export async function listApplicationSuggestionPage(page: number): Promise<ApplicationPage> {
  const response = await apiClient.get("/api/v1/applications/", {
    params: { page, page_size: 100 },
    _skipAuthRefresh: true,
  } as AuthRequestConfig);
  return mapPage(response.data as Record<string, unknown>);
}

export async function getApplication(id: number | string): Promise<JobApplication> {
  const response = await apiClient.get(`/api/v1/applications/${id}/`);
  return mapApplication(response.data as Record<string, unknown>);
}

export async function createApplication(payload: Record<string, unknown>): Promise<JobApplication> {
  const response = await apiClient.post("/api/v1/applications/", toSnakePayload(payload));
  return mapApplication(response.data as Record<string, unknown>);
}

export async function updateApplication(
  id: number | string,
  payload: Record<string, unknown>,
): Promise<JobApplication> {
  const response = await apiClient.patch(`/api/v1/applications/${id}/`, toSnakePayload(payload));
  return mapApplication(response.data as Record<string, unknown>);
}

export async function deleteApplication(id: number | string): Promise<void> {
  await apiClient.delete(`/api/v1/applications/${id}/`);
}

export async function deletePosition(companyId: number | string, positionId: number): Promise<void> {
  await apiClient.delete(`/api/v1/applications/${companyId}/positions/${positionId}/`);
}

export async function deleteInterview(companyId: number | string, positionId: number, interviewId: number): Promise<void> {
  await apiClient.delete(`/api/v1/applications/${companyId}/positions/${positionId}/interviews/${interviewId}/`);
}

export async function createInterview(companyId: number | string, positionId: number, payload: Record<string, unknown>) {
  const response = await apiClient.post(`/api/v1/applications/${companyId}/positions/${positionId}/interviews/`, toSnakePayload(payload));
  return readInterview(response.data);
}

export async function updateInterview(companyId: number | string, positionId: number, interviewId: number, payload: Record<string, unknown>) {
  const response = await apiClient.patch(`/api/v1/applications/${companyId}/positions/${positionId}/interviews/${interviewId}/`, toSnakePayload(payload));
  return readInterview(response.data);
}

export const fetchApplications = listApplications;
export const getApplications = listApplications;
export const list = listApplications;
export const patchApplication = updateApplication;
export const editApplication = updateApplication;
export const update = updateApplication;
export const create = createApplication;
export { deleteApplication as delete };
