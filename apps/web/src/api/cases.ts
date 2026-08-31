import { requestJson } from '@/api/client';
import type { components } from '@/api/generated/schema';

export type CaseDetailResponse = components['schemas']['CaseDetailResponse'];
export type CasesResponse = components['schemas']['CasesResponse'];
export type ConfirmFactsRequest = components['schemas']['ConfirmFactsRequest'];
export type CreateCaseRequest = components['schemas']['CreateCaseRequest'];

export function listCases(accessToken: string): Promise<CasesResponse> {
  return requestJson<CasesResponse>('/api/v1/cases', {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
}

export function getCase(caseId: string, accessToken: string): Promise<CaseDetailResponse> {
  return requestJson<CaseDetailResponse>(`/api/v1/cases/${caseId}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
}

export function createCase(
  payload: CreateCaseRequest,
  accessToken: string,
): Promise<CaseDetailResponse> {
  return requestJson<CaseDetailResponse>('/api/v1/cases', {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify(payload),
  });
}

export function confirmCaseFacts(
  caseId: string,
  payload: ConfirmFactsRequest,
  accessToken: string,
): Promise<CaseDetailResponse> {
  return requestJson<CaseDetailResponse>(`/api/v1/cases/${caseId}/facts/confirm`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify(payload),
  });
}
