import { afterEach, describe, expect, it, vi } from 'vitest';

import { submitQueryRun } from '@/api/queryRuns';

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('submitQueryRun', () => {
  it('submits an authenticated controlled query for a case', async () => {
    let capturedInit: RequestInit | undefined;
    vi.stubGlobal(
      'fetch',
      vi.fn((_input: RequestInfo | URL, init?: RequestInit) => {
        capturedInit = init;
        return Promise.resolve(
          new Response(JSON.stringify({ data: {}, meta: { request_id: 'request-789' } }), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          }),
        );
      }),
    );

    await submitQueryRun('case-001', { query: '这项优惠是否适用' }, 'access-token-for-test');

    expect(capturedInit?.method).toBe('POST');
    expect(capturedInit?.body).toContain('这项优惠是否适用');
  });
});
