import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  addOrganizationMember,
  getCurrentMembership,
  listOrganizationMembers,
  updateOrganizationMember,
} from '@/api/organizations';

afterEach(() => {
  vi.unstubAllGlobals();
});

function mockJsonResponse(data: unknown) {
  return new Response(JSON.stringify(data), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('organization API client', () => {
  it('reads the current membership and organization members with bearer authorization', async () => {
    const fetchMock = vi.fn(() => Promise.resolve(mockJsonResponse({ data: {}, membership: {}, meta: { request_id: 'request-001' } })));
    vi.stubGlobal('fetch', fetchMock);

    await getCurrentMembership('token-001');
    await listOrganizationMembers('org-001', 'token-001');

    expect(fetchMock).toHaveBeenNthCalledWith(1, '/api/v1/me', expect.anything());
    expect(fetchMock).toHaveBeenNthCalledWith(2, '/api/v1/organizations/org-001/members', expect.anything());
  });

  it('creates and version-updates an organization member', async () => {
    let capturedInit: RequestInit | undefined;
    const fetchMock = vi.fn((_input: RequestInfo | URL, init?: RequestInit) => {
      capturedInit = init;
      return Promise.resolve(mockJsonResponse({ data: {}, meta: { request_id: 'request-002' } }));
    });
    vi.stubGlobal('fetch', fetchMock);

    await addOrganizationMember('org-001', { email: 'new.user@example.com', role_code: 'consultant' }, 'token-001');
    await updateOrganizationMember('org-001', 'member-001', { role_code: 'reviewer', status: 'active', version_no: 3 }, 'token-001');

    expect(fetchMock).toHaveBeenNthCalledWith(1, '/api/v1/organizations/org-001/members', expect.anything());
    expect(fetchMock).toHaveBeenNthCalledWith(2, '/api/v1/organizations/org-001/members/member-001', expect.anything());
    expect(capturedInit?.method).toBe('PATCH');
    expect(capturedInit?.body).toContain('version_no');
  });
});
