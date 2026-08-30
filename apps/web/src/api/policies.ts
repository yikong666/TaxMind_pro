import { requestJson } from '@/api/client';
import type { components } from '@/api/generated/schema';

export type PolicySearchResponse = components['schemas']['PolicySearchResponse'];

export interface PolicySearchInput {
  query: string;
  regionCode: string;
  businessDate: string;
}

export function searchPolicies(
  input: PolicySearchInput,
  accessToken: string,
): Promise<PolicySearchResponse> {
  const parameters = new URLSearchParams({
    query: input.query,
    region_code: input.regionCode,
    business_date: input.businessDate,
  });
  return requestJson<PolicySearchResponse>(`/api/v1/policies/search?${parameters.toString()}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
}
