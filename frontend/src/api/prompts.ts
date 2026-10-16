import { apiClient } from "./http";

export interface Prompt {
  id: number;
  title: string;
  content: string;
  is_preset: boolean;
  created_at: string;
  updated_at: string;
}

export interface PromptPage { count: number; page: number; page_size: number; total_pages: number; next: string | null; previous: string | null; results: Prompt[]; }

export async function listPrompts(search = ""): Promise<PromptPage> {
  const response = await apiClient.get("/api/v1/prompts/", { params: search ? { search } : undefined });
  return response.data as PromptPage;
}
export async function createPrompt(payload: { title: string; content: string }): Promise<Prompt> {
  const response = await apiClient.post("/api/v1/prompts/", payload); return response.data as Prompt;
}
export async function updatePrompt(id: number, payload: Partial<Pick<Prompt, "title" | "content">>): Promise<Prompt> {
  const response = await apiClient.patch(`/api/v1/prompts/${id}/`, payload); return response.data as Prompt;
}
export async function deletePrompt(id: number): Promise<void> { await apiClient.delete(`/api/v1/prompts/${id}/`); }
