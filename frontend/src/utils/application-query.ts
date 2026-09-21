import {
  APPLICATION_PAGE_SIZES,
  type ApplicationPageSize,
  type ApplicationQueryState,
} from "../types/application";

export const DEFAULT_PAGE = 1;
export const DEFAULT_PAGE_SIZE: ApplicationPageSize = 20;
export const DEFAULT_ORDERING = "-updated_at";

type QueryInput = Record<string, unknown> | URLSearchParams;

function readValue(query: QueryInput, key: string, aliases: string[] = []): string | undefined {
  const keys = [key, ...aliases];
  for (const candidate of keys) {
    if (query instanceof URLSearchParams) {
      const value = query.get(candidate);
      if (value !== null) return value;
      continue;
    }
    const value = query[candidate];
    if (Array.isArray(value)) return value.length > 0 ? String(value[0]) : undefined;
    if (value !== undefined && value !== null) return String(value);
  }
  return undefined;
}

function parsePositiveInteger(value: string | undefined, fallback: number): number {
  if (!value || !/^\d+$/.test(value)) return fallback;
  const parsed = Number(value);
  return Number.isSafeInteger(parsed) && parsed >= 1 ? parsed : fallback;
}

function parsePageSize(value: string | undefined): ApplicationPageSize {
  if (!value || !/^\d+$/.test(value)) return DEFAULT_PAGE_SIZE;
  const parsed = Number(value);
  return APPLICATION_PAGE_SIZES.includes(parsed as ApplicationPageSize)
    ? (parsed as ApplicationPageSize)
    : DEFAULT_PAGE_SIZE;
}

function optionalString(value: string | undefined): string | undefined {
  return value ? value : undefined;
}

export function parseApplicationQuery(query: QueryInput = {}): ApplicationQueryState {
  const search = readValue(query, "search") ?? "";
  const applicationStatus = optionalString(readValue(query, "applicationStatus", ["application_status"])) as
    | ApplicationQueryState["applicationStatus"]
    | undefined;
  const stage = optionalString(readValue(query, "stage")) as ApplicationQueryState["stage"] | undefined;

  return {
    page: parsePositiveInteger(readValue(query, "page"), DEFAULT_PAGE),
    pageSize: parsePageSize(readValue(query, "pageSize", ["page_size"])),
    search,
    ...(applicationStatus ? { applicationStatus } : {}),
    ...(stage ? { stage } : {}),
    ...(optionalString(readValue(query, "applicationTimeAfter", ["application_time_after"]))
      ? { applicationTimeAfter: readValue(query, "applicationTimeAfter", ["application_time_after"]) }
      : {}),
    ...(optionalString(readValue(query, "applicationTimeBefore", ["application_time_before"]))
      ? { applicationTimeBefore: readValue(query, "applicationTimeBefore", ["application_time_before"]) }
      : {}),
    ordering: readValue(query, "ordering") || DEFAULT_ORDERING,
  };
}

export function serializeApplicationQuery(state: Partial<ApplicationQueryState> = {}): Record<string, string> {
  const normalized = parseApplicationQuery(state as QueryInput);
  const result: Record<string, string> = {
    page: String(normalized.page),
    pageSize: String(normalized.pageSize),
  };

  if (normalized.search) result.search = normalized.search;
  if (normalized.applicationStatus) result.applicationStatus = normalized.applicationStatus;
  if (normalized.stage) result.stage = normalized.stage;
  if (normalized.applicationTimeAfter) result.applicationTimeAfter = normalized.applicationTimeAfter;
  if (normalized.applicationTimeBefore) result.applicationTimeBefore = normalized.applicationTimeBefore;
  if (normalized.ordering) result.ordering = normalized.ordering;
  return result;
}

export const parseQuery = parseApplicationQuery;
export const fromUrlQuery = parseApplicationQuery;
export const serializeQuery = serializeApplicationQuery;
export const toUrlQuery = serializeApplicationQuery;

