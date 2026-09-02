import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  appendUserMessage,
  createConversation,
  deleteConversation,
  restoreConversation,
} from '@/api/conversations';

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('conversation API', () => {
  it('creates a conversation inside the selected case', async () => {
    const fetchMock = vi.fn(() =>
      Promise.resolve(
        new Response(JSON.stringify({ data: {}, meta: { request_id: 'request-001' } }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    );
    vi.stubGlobal('fetch', fetchMock);

    await createConversation('case-001', { title: '虚构咨询会话' }, 'access-token');

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/cases/case-001/conversations',
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('sends an idempotent user message', async () => {
    let capturedInit: RequestInit | undefined;
    const fetchMock = vi.fn((_input: RequestInfo | URL, init?: RequestInit) => {
      capturedInit = init;
      return Promise.resolve(
        new Response(JSON.stringify({ data: {}, meta: { request_id: 'request-002' } }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      );
    });
    vi.stubGlobal('fetch', fetchMock);

    await appendUserMessage(
      'conversation-001',
      { text: '虚构咨询消息', idempotency_key: 'message-001' },
      'access-token',
    );

    expect(capturedInit?.body).toContain('idempotency_key');
  });

  it('soft deletes and restores a conversation through governed lifecycle routes', async () => {
    const fetchMock = vi.fn(() =>
      Promise.resolve(
        new Response(JSON.stringify({ data: {}, meta: { request_id: 'request-003' } }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    );
    vi.stubGlobal('fetch', fetchMock);

    await deleteConversation('conversation-001', 'access-token');
    await restoreConversation('conversation-001', 'access-token');

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      '/api/v1/conversations/conversation-001',
      expect.objectContaining({ method: 'DELETE' }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      '/api/v1/conversations/conversation-001/restore',
      expect.objectContaining({ method: 'POST' }),
    );
  });
});
