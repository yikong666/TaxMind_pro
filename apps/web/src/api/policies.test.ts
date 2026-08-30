import { afterEach, describe, expect, it, vi } from 'vitest';

import { searchPolicies } from '@/api/policies';

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('searchPolicies', () => {
  it('sends the authenticated, date-scoped search request', async () => {
    let capturedUrl = '';
    let capturedInit: RequestInit | undefined;
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      capturedUrl =
        typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url;
      capturedInit = init;
      return Promise.resolve(
        new Response(JSON.stringify({ data: [], meta: { request_id: 'request-123' } }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      );
    });
    vi.stubGlobal('fetch', fetchMock);

    await searchPolicies(
      { query: '小规模 纳税人', regionCode: '440300', businessDate: '2026-08-31' },
      'access-token-for-test',
    );

    expect(capturedUrl).toBe(
      '/api/v1/policies/search?query=%E5%B0%8F%E8%A7%84%E6%A8%A1+%E7%BA%B3%E7%A8%8E%E4%BA%BA&region_code=440300&business_date=2026-08-31',
    );
    expect(capturedInit?.headers).toBeInstanceOf(Headers);
    if (!(capturedInit?.headers instanceof Headers)) {
      throw new Error('request headers were not created');
    }
    expect(capturedInit.headers.get('Authorization')).toBe('Bearer access-token-for-test');
  });
});
