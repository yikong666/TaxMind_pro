import { afterEach, describe, expect, it, vi } from 'vitest';

import { confirmCaseFacts, listCases } from '@/api/cases';

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('confirmCaseFacts', () => {
  it('sends the immutable fact-confirmation request', async () => {
    let capturedInit: RequestInit | undefined;
    const fetchMock = vi.fn((_input: RequestInfo | URL, init?: RequestInit) => {
      capturedInit = init;
      return Promise.resolve(
        new Response(JSON.stringify({ data: {}, meta: { request_id: 'request-456' } }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      );
    });
    vi.stubGlobal('fetch', fetchMock);

    await confirmCaseFacts(
      'case-001',
      {
        profile_version: 1,
        fact_proposals: [
          { fact_key: 'invoice_intent', value_type: 'text', value: '虚构开票咨询' },
        ],
        confirmed_fact_keys: ['invoice_intent'],
        rejected_fact_keys: [],
      },
      'access-token-for-test',
    );

    expect(fetchMock).toHaveBeenCalledWith('/api/v1/cases/case-001/facts/confirm', expect.anything());
    expect(capturedInit?.method).toBe('POST');
    expect(capturedInit?.body).toContain('confirmed_fact_keys');
  });
});

describe('listCases', () => {
  it('sends the authenticated case-list request', async () => {
    let capturedInit: RequestInit | undefined;
    const fetchMock = vi.fn((_input: RequestInfo | URL, init?: RequestInit) => {
      capturedInit = init;
      return Promise.resolve(
        new Response(JSON.stringify({ data: [], meta: { request_id: 'request-123' } }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      );
    });
    vi.stubGlobal('fetch', fetchMock);

    await listCases('access-token-for-test');

    expect(fetchMock).toHaveBeenCalledWith('/api/v1/cases', expect.anything());
    expect(capturedInit?.headers).toBeInstanceOf(Headers);
    if (!(capturedInit?.headers instanceof Headers)) {
      throw new Error('request headers were not created');
    }
    expect(capturedInit.headers.get('Authorization')).toBe('Bearer access-token-for-test');
  });
});
