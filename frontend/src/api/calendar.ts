import { apiClient } from "./http";

export type CalendarStage =
  | "ai_interview"
  | "written_test"
  | "first_interview"
  | "second_interview"
  | "third_interview"
  | "hr_interview";

export interface CalendarEvent {
  application_id: number;
  company_name: string;
  position_name: string;
  stage: CalendarStage;
  start_at: string;
  end_at: string;
  duration_minutes: number;
}

export interface CalendarEventResponse {
  timezone: "Asia/Shanghai";
  start: string;
  end: string;
  events: CalendarEvent[];
}

export async function getCalendarEvents(
  start: string,
  end: string,
): Promise<CalendarEventResponse> {
  const response = await apiClient.request({
    url: "/api/v1/calendar/events/",
    method: "get",
    params: { start, end },
  });
  return response.data as CalendarEventResponse;
}
