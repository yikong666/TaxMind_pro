import { requestJson } from '@/api/client';
import type { components } from '@/api/generated/schema';

export type QueryRunRequest = components['schemas']['QueryRunRequest'];
export type QueryRunResponse = components['schemas']['QueryRunResponse'];

export function submitQueryRun(
  caseId: string,
  payload: QueryRunRequest,
  accessToken: string,
): Promise<QueryRunResponse> {
  return requestJson<QueryRunResponse>(`/api/v1/cases/${caseId}/query-runs`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify(payload),
  });
}
