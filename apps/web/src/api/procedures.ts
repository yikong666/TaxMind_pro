import { requestJson } from '@/api/client';

import type { components } from '@/api/generated/schema';

export type ProcedureSearchResponse = components['schemas']['ProcedureSearchResponse'];

export function searchProcedures(
  query: string,
  regionCode: string,
  businessDate: string,
  accessToken: string,
): Promise<ProcedureSearchResponse> {
  const params = new URLSearchParams({ query, region_code: regionCode, business_date: businessDate });
  return requestJson(`/api/v1/procedures/search?${params.toString()}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
}
