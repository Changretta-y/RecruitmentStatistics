export const APPLICATION_PAGE_SIZES = [10, 20, 50, 100] as const;

export type ApplicationPageSize = (typeof APPLICATION_PAGE_SIZES)[number];

export const APPLICATION_STATUS_OPTIONS = [
  { value: "applied", title: "投递" },
  { value: "assessment", title: "测评" },
  { value: "written_test", title: "笔试" },
  { value: "first_interview", title: "一面" },
  { value: "second_interview", title: "二面" },
  { value: "other_interview", title: "其他轮次" },
  { value: "hr_interview", title: "HR面" },
  { value: "rejected", title: "拒绝" },
] as const;

export type ApplicationStatus = (typeof APPLICATION_STATUS_OPTIONS)[number]["value"];
export const APPLICATION_STATUS_LABELS: Record<ApplicationStatus, string> = Object.fromEntries(
  APPLICATION_STATUS_OPTIONS.map(({ value, title }) => [value, title]),
) as Record<ApplicationStatus, string>;

export type ApplicationStage =
  | "ai_interview"
  | "assessment"
  | "written_test"
  | "first_interview"
  | "second_interview"
  | "third_interview"
  | "hr_interview";

export type ApplicationCurrentStage = ApplicationStatus;

export interface Company {
  id: number;
  companyName: string;
  recruitmentUrl: string | null;
  createdAt?: string;
  updatedAt?: string;
}

export interface JobApplication {
  id: number;
  user: number;
  companyId: number;
  company: Company;
  companyName: string;
  recruitmentUrl: string | null;
  positionName: string;
  applicationUrl: string;
  applicationStatus: ApplicationStatus;
  currentStage: ApplicationCurrentStage | null;
  sharedStages?: SharedApplicationStage[];
  positions?: ApplicationPosition[];
  applicationTime: string | null;
  aiInterviewTime: string | null;
  aiInterviewDurationMinutes: number | null;
  writtenTestTime: string | null;
  writtenTestDurationMinutes: number | null;
  firstInterviewTime: string | null;
  firstInterviewDurationMinutes: number | null;
  secondInterviewTime: string | null;
  secondInterviewDurationMinutes: number | null;
  thirdInterviewTime: string | null;
  thirdInterviewDurationMinutes: number | null;
  hrInterviewTime: string | null;
  hrInterviewDurationMinutes: number | null;
  notes: string;
  createdAt: string;
  updatedAt: string;
}

export type SharedStageType = "ai_interview" | "assessment" | "written_test";

export interface ApplicationInterview {
  id?: number;
  name: string;
  scheduledAt: string | null;
  durationMinutes: number | null;
}

export interface SharedApplicationStage extends Omit<ApplicationInterview, "id" | "name"> {
  type: SharedStageType;
}

export interface ApplicationPosition {
  id?: number;
  positionName: string;
  applicationUrl?: string | null;
  applicationStatus: ApplicationStatus;
  currentStage: ApplicationCurrentStage;
  applicationTime: string | null;
  notes: string;
  interviews: ApplicationInterview[];
}

export interface ApplicationPage {
  count: number;
  page: number;
  pageSize: number;
  totalPages: number;
  next: string | null;
  previous: string | null;
  results: JobApplication[];
}

export type ApplicationListResponse = ApplicationPage;

export interface UnifiedApiError {
  code: string;
  message?: string;
  details?: Record<string, unknown>;
}

export type ApiError = UnifiedApiError;

export interface ApplicationQueryState {
  page: number;
  pageSize: ApplicationPageSize;
  search: string;
  applicationStatus?: ApplicationStatus | ApplicationStatus[];
  applicationTimeAfter?: string;
  applicationTimeBefore?: string;
  ordering: string;
}

export type ApplicationQuery = Partial<ApplicationQueryState>;
