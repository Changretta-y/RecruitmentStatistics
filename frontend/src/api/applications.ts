import { apiClient } from "./http";
import {
  type ApplicationPage,
  type ApplicationQuery,
  type JobApplication,
} from "../types/application";
import { parseApplicationQuery } from "../utils/application-query";

const applicationFieldMap: Record<string, string> = {
  companyName: "company_name",
  positionName: "position_name",
  applicationStatus: "application_status",
  currentStage: "current_stage",
  applicationTime: "application_time",
  aiInterviewTime: "ai_interview_time",
  writtenTestTime: "written_test_time",
  firstInterviewTime: "first_interview_time",
  secondInterviewTime: "second_interview_time",
  thirdInterviewTime: "third_interview_time",
  hrInterviewTime: "hr_interview_time",
  createdAt: "created_at",
  updatedAt: "updated_at",
};

function mapApplication(value: Record<string, unknown>): JobApplication {
  const get = (snake: string, camel: string): unknown => value[snake] ?? value[camel];
  return {
    id: value.id as number,
    user: value.user as number,
    companyName: get("company_name", "companyName") as string,
    positionName: get("position_name", "positionName") as string,
    applicationStatus: get("application_status", "applicationStatus") as JobApplication["applicationStatus"],
    currentStage: (get("current_stage", "currentStage") as JobApplication["currentStage"]) ?? null,
    applicationTime: (get("application_time", "applicationTime") as string | null) ?? null,
    aiInterviewTime: (get("ai_interview_time", "aiInterviewTime") as string | null) ?? null,
    writtenTestTime: (get("written_test_time", "writtenTestTime") as string | null) ?? null,
    firstInterviewTime: (get("first_interview_time", "firstInterviewTime") as string | null) ?? null,
    secondInterviewTime: (get("second_interview_time", "secondInterviewTime") as string | null) ?? null,
    thirdInterviewTime: (get("third_interview_time", "thirdInterviewTime") as string | null) ?? null,
    hrInterviewTime: (get("hr_interview_time", "hrInterviewTime") as string | null) ?? null,
    notes: (get("notes", "notes") as string) ?? "",
    createdAt: get("created_at", "createdAt") as string,
    updatedAt: get("updated_at", "updatedAt") as string,
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

function toSnakePayload(payload: Record<string, unknown>): Record<string, unknown> {
  const result: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(payload)) {
    if (value === undefined) continue;
    if (key === "id" || key === "user" || key === "createdAt" || key === "updatedAt" || key === "currentStage") {
      continue;
    }
    result[applicationFieldMap[key] ?? key] = value;
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
  if (normalized.applicationStatus) params.application_status = normalized.applicationStatus;
  if (normalized.stage) params.stage = normalized.stage;
  if (normalized.applicationTimeAfter) params.application_time_after = normalized.applicationTimeAfter;
  if (normalized.applicationTimeBefore) params.application_time_before = normalized.applicationTimeBefore;
  if (normalized.ordering) params.ordering = normalized.ordering;
  return params;
}

export async function listApplications(query: ApplicationQuery = {}): Promise<ApplicationPage> {
  const response = await apiClient.get("/api/v1/applications/", { params: apiQuery(query) });
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

export const fetchApplications = listApplications;
export const getApplications = listApplications;
export const list = listApplications;
export const patchApplication = updateApplication;
export const editApplication = updateApplication;
export const update = updateApplication;
export const create = createApplication;
export { deleteApplication as delete };
