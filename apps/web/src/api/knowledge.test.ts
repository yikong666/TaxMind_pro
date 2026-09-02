import { afterEach, describe, expect, it, vi } from 'vitest';

import { registerKnowledgeSource, reviewKnowledgeCandidate, uploadKnowledgeDocument } from '@/api/knowledge';

afterEach(() => {
  vi.unstubAllGlobals();
});

function mockJsonResponse(data: unknown) {
  return new Response(JSON.stringify(data), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('knowledge API client', () => {
  it('submits a single candidate review with bearer authorization', async () => {
    let capturedInit: RequestInit | undefined;
    const fetchMock = vi.fn((_input: RequestInfo | URL, init?: RequestInit) => {
      capturedInit = init;
      return Promise.resolve(mockJsonResponse({ data: {}, meta: { request_id: 'request-001' } }));
    });
    vi.stubGlobal('fetch', fetchMock);

    await reviewKnowledgeCandidate('candidate-001', { decision: 'rejected', reason: '来源字段缺失' }, 'token-001');

    expect(fetchMock).toHaveBeenCalledWith('/api/v1/knowledge/candidates/candidate-001/review', expect.anything());
    expect(capturedInit?.method).toBe('POST');
    expect(new Headers(capturedInit?.headers).get('Authorization')).toBe('Bearer token-001');
    expect(capturedInit?.body).toBe(JSON.stringify({ decision: 'rejected', reason: '来源字段缺失' }));
  });

  it('registers source metadata without triggering an ingestion job', async () => {
    let capturedInit: RequestInit | undefined;
    const fetchMock = vi.fn((_input: RequestInfo | URL, init?: RequestInit) => {
      capturedInit = init;
      return Promise.resolve(mockJsonResponse({ data: {}, meta: { request_id: 'request-002' } }));
    });
    vi.stubGlobal('fetch', fetchMock);

    await registerKnowledgeSource({
      name: '深圳税务政策公开栏目',
      authority_name: '国家税务总局深圳市税务局',
      base_url: 'https://shenzhen.chinatax.gov.cn/',
      region_code: '440300',
      source_level: 'A',
      collection_method: 'manual',
    }, 'token-001');

    expect(fetchMock).toHaveBeenCalledWith('/api/v1/knowledge/sources', expect.anything());
    expect(capturedInit?.method).toBe('POST');
    expect(capturedInit?.body).toContain('深圳税务政策公开栏目');
  });

  it('uploads an authorized local document as multipart form data', async () => {
    let capturedInit: RequestInit | undefined;
    const fetchMock = vi.fn((_input: RequestInfo | URL, init?: RequestInit) => {
      capturedInit = init;
      return Promise.resolve(mockJsonResponse({ data: {}, meta: { request_id: 'request-003' } }));
    });
    vi.stubGlobal('fetch', fetchMock);

    await uploadKnowledgeDocument({
      sourceSiteId: '00000000-0000-0000-0000-000000000001',
      title: '虚构政策公告',
      issuingAuthority: '虚构测试机关',
      regionCode: '440300',
      canonicalUrl: 'https://example.invalid/policy/001',
      file: new File(['test document'], 'policy.txt', { type: 'text/plain' }),
    }, 'token-001');

    expect(fetchMock).toHaveBeenCalledWith('/api/v1/knowledge/uploads', expect.anything());
    expect(capturedInit?.method).toBe('POST');
    expect(capturedInit?.body).toBeInstanceOf(FormData);
    expect(new Headers(capturedInit?.headers).has('Content-Type')).toBe(false);
  });
});
