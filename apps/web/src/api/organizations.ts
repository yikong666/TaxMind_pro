import { requestJson } from '@/api/client';
import type { components } from '@/api/generated/schema';

export type MeResponse = components['schemas']['MeResponse'];
export type MemberCreateRequest = components['schemas']['MemberCreateRequest'];
export type MemberResponse = components['schemas']['MemberResponse'];
export type MembersResponse = components['schemas']['MembersResponse'];
export type MemberUpdateRequest = components['schemas']['MemberUpdateRequest'];

function authorization(accessToken: string) {
  return { Authorization: `Bearer ${accessToken}` };
}

export function getCurrentMembership(accessToken: string): Promise<MeResponse> {
  return requestJson<MeResponse>('/api/v1/me', { headers: authorization(accessToken) });
}

export function listOrganizationMembers(
  orgId: string,
  accessToken: string,
): Promise<MembersResponse> {
  return requestJson<MembersResponse>(`/api/v1/organizations/${orgId}/members`, {
    headers: authorization(accessToken),
  });
}

export function addOrganizationMember(
  orgId: string,
  payload: MemberCreateRequest,
  accessToken: string,
): Promise<MemberResponse> {
  return requestJson<MemberResponse>(`/api/v1/organizations/${orgId}/members`, {
    method: 'POST',
    headers: authorization(accessToken),
    body: JSON.stringify(payload),
  });
}

export function updateOrganizationMember(
  orgId: string,
  memberId: string,
  payload: MemberUpdateRequest,
  accessToken: string,
): Promise<MemberResponse> {
  return requestJson<MemberResponse>(`/api/v1/organizations/${orgId}/members/${memberId}`, {
    method: 'PATCH',
    headers: authorization(accessToken),
    body: JSON.stringify(payload),
  });
}
