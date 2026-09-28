import { apiClient } from "./http";
import type { SharedApplicationPage, SharingConnection, SharingHistory, SharingRequest, SharingUser } from "../types/sharing";

const base = "/api/v1/sharing/";
export async function sharingMe(): Promise<SharingUser> { return (await apiClient.get(base + "me/")).data; }
export async function recommendations(): Promise<SharingUser[]> { return (await apiClient.get(base + "users/recommendations/")).data.results; }
export async function searchUser(id: string): Promise<SharingUser> { return (await apiClient.get(base + `users/${id}/`)).data; }
export async function requestHistory(): Promise<SharingHistory> { return (await apiClient.get(base + "requests/")).data; }
export async function connections(): Promise<SharingConnection[]> { return (await apiClient.get(base + "connections/")).data.results; }
export async function sendRequest(recipientId: number): Promise<SharingRequest> { return (await apiClient.post(base + "requests/", { recipient_id: recipientId })).data; }
export async function respondRequest(id: number, decision: "accepted" | "rejected"): Promise<SharingRequest> {
  return (await apiClient.post(base + `requests/${id}/respond/`, { decision })).data;
}
export async function revokeConnection(id: number): Promise<void> { await apiClient.delete(base + `connections/${id}/`); }
export async function sharedApplications(id: number, page: number, pageSize: number, search: string): Promise<SharedApplicationPage> {
  return (await apiClient.get(base + `users/${id}/applications/`, { params: { page, page_size: pageSize, ...(search ? { search } : {}) } })).data;
}
