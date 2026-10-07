import type { ApplicationStatus } from "./application";

export interface SharingUser {
  id: number;
  username: string;
  avatar: string;
  relationship: "none" | "outgoing_pending" | "incoming_pending" | "connected";
}

export interface SharingRequest {
  id: number;
  sender: SharingUser;
  recipient: SharingUser;
  status: "pending" | "accepted" | "rejected" | "revoked";
  created_at: string;
  responded_at: string | null;
}

export interface SharingConnection { id: number; user: SharingUser; created_at: string }
export interface SharingHistory { incoming: SharingRequest[]; outgoing: SharingRequest[] }
export interface SharedApplication {
  id: number;
  company_name: string;
  position_name: string;
  application_url: string;
  application_status: ApplicationStatus;
  current_stage: ApplicationStatus;
  application_time: string | null;
  created_at: string;
  updated_at: string;
  [key: string]: string | number | null;
}
export interface SharedApplicationPage {
  count: number;
  page: number;
  page_size: number;
  total_pages: number;
  results: SharedApplication[];
}
