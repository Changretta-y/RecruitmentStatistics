export const APPLICATION_PAGE_SIZES = [10, 20, 50, 100] as const;

export type ApplicationPageSize = (typeof APPLICATION_PAGE_SIZES)[number];

export type ApplicationStatus =
  | "applied"
  | "in_progress"
  | "offer"
  | "rejected"
  | "withdrawn";

export type ApplicationStage =
  | "ai_interview"
  | "assessment"
  | "written_test"
  | "first_interview"
  | "second_interview"
  | "third_interview"
  | "hr_interview";

export type ApplicationCurrentStage =
  | ApplicationStage
  | "applied"
  | "offer"
  | "rejected"
  | "withdrawn";

export interface JobApplication {
  id: number;
  user: number;
  companyName: string;
  positionName: string;
  applicationUrl: string;
  applicationStatus: ApplicationStatus;
  currentStage: ApplicationCurrentStage | string | null;
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
  applicationUrl: string;
  applicationStatus: ApplicationStatus;
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
  stage?: ApplicationStage;
  applicationTimeAfter?: string;
  applicationTimeBefore?: string;
  ordering: string;
}

export type ApplicationQuery = Partial<ApplicationQueryState>;
