import { apiClient } from "./http";
import type { Company } from "../types/application";

function mapCompany(value: Record<string, unknown>): Company {
  return {
    id: Number(value.id),
    companyName: String(value.company_name ?? value.companyName ?? ""),
    recruitmentUrl: (value.recruitment_url ?? value.recruitmentUrl ?? null) as string | null,
    ...(value.created_at || value.createdAt ? { createdAt: String(value.created_at ?? value.createdAt) } : {}),
    ...(value.updated_at || value.updatedAt ? { updatedAt: String(value.updated_at ?? value.updatedAt) } : {}),
  };
}

function bodyOf(value: unknown): Record<string, unknown> {
  if (value && typeof value === "object") {
    const record = value as Record<string, unknown>;
    if (record.data && typeof record.data === "object" && !Array.isArray(record.data)) return record.data as Record<string, unknown>;
    return record;
  }
  return {};
}

export async function listCompanies(search = ""): Promise<{ results: Company[]; count: number }> {
  const response = await apiClient.get("/api/v1/companies/", { params: { search, page: 1, page_size: 100, ordering: "company_name" } });
  const body = bodyOf(response.data);
  const results = Array.isArray(body.results) ? body.results.map(item => mapCompany(item as Record<string, unknown>)) : [];
  return { results, count: Number(body.count ?? results.length) };
}

export async function getCompany(id: number | string): Promise<Company> {
  const response = await apiClient.get(`/api/v1/companies/${id}/`);
  return mapCompany(bodyOf(response.data));
}

export async function createCompany(payload: { companyName: string; recruitmentUrl?: string | null }): Promise<Company> {
  const response = await apiClient.post("/api/v1/companies/", {
    company_name: payload.companyName,
    recruitment_url: payload.recruitmentUrl || null,
  });
  return mapCompany(bodyOf(response.data));
}

export async function updateCompany(id: number | string, payload: { companyName?: string; recruitmentUrl?: string | null }): Promise<Company> {
  const value: Record<string, unknown> = {};
  if (payload.companyName !== undefined) value.company_name = payload.companyName;
  if (payload.recruitmentUrl !== undefined) value.recruitment_url = payload.recruitmentUrl || null;
  const response = await apiClient.patch(`/api/v1/companies/${id}/`, value);
  return mapCompany(bodyOf(response.data));
}
