import { afterEach, describe, expect, it, vi } from 'vitest';

import { getQueryRun, submitQueryRun } from '@/api/queryRuns';

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

    await submitQueryRun(
      'case-001',
      {
        query: '这项优惠是否适用',
        conversation_id: 'conversation-001',
        idempotency_key: 'query-run-key-001',
      },
      'access-token-for-test',
    );

    expect(capturedInit?.method).toBe('POST');
    expect(capturedInit?.body).toContain('这项优惠是否适用');
  });

  it('reads an authenticated persisted query run', async () => {
    let capturedUrl: RequestInfo | URL | undefined;
    let capturedInit: RequestInit | undefined;
    vi.stubGlobal(
      'fetch',
      vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
        capturedUrl = input;
        capturedInit = init;
        return Promise.resolve(
          new Response(JSON.stringify({ data: {}, meta: { request_id: 'request-790' } }), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          }),
        );
      }),
    );

    await getQueryRun('run-001', 'access-token-for-test');

    expect(capturedUrl).toContain('/api/v1/query-runs/run-001');
    expect(new Headers(capturedInit?.headers).get('Authorization')).toBe(
      'Bearer access-token-for-test',
    );
  });
});
