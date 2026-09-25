import { apiClient } from "./http";

export type DeliveryStatus = "pending" | "sending" | "accepted" | "failed_retryable" | "failed" | "unknown";

export interface NotificationSettings {
  recipient_email: string;
  daily_time: string;
  enabled: boolean;
  verified: boolean;
  timezone: "Asia/Shanghai";
  last_delivery: { date: string; status: DeliveryStatus } | null;
}

export async function getNotificationSettings(): Promise<NotificationSettings> {
  const response = await apiClient.get("/api/v1/notification-settings/");
  return response.data as NotificationSettings;
}

export async function saveNotificationSettings(
  settings: Pick<NotificationSettings, "recipient_email" | "daily_time" | "enabled">,
): Promise<NotificationSettings> {
  const response = await apiClient.patch("/api/v1/notification-settings/", settings);
  return response.data as NotificationSettings;
}

export async function requestNotificationVerification(): Promise<void> {
  await apiClient.post("/api/v1/notification-settings/verification/");
}

export async function verifyNotificationAddress(token: string): Promise<NotificationSettings> {
  const response = await apiClient.post("/api/v1/notification-settings/verify/", { token });
  return response.data as NotificationSettings;
}
