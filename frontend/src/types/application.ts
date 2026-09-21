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
  | "written_test"
  | "first_interview"
  | "second_interview"
  | "third_interview"
  | "hr_interview";

export interface JobApplication {
  id: number;
  user: number;
  companyName: string;
  positionName: string;
  applicationStatus: ApplicationStatus;
  currentStage: ApplicationStage | null;
  applicationTime: string | null;
  aiInterviewTime: string | null;
  writtenTestTime: string | null;
  firstInterviewTime: string | null;
  secondInterviewTime: string | null;
  thirdInterviewTime: string | null;
  hrInterviewTime: string | null;
  notes: string;
  createdAt: string;
  updatedAt: string;
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
  applicationStatus?: ApplicationStatus;
  stage?: ApplicationStage;
  applicationTimeAfter?: string;
  applicationTimeBefore?: string;
  ordering: string;
}

export type ApplicationQuery = Partial<ApplicationQueryState>;

