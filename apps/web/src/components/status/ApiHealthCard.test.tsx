import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { ApiHealthCard } from '@/components/status/ApiHealthCard';

function renderCard() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <ApiHealthCard />
    </QueryClientProvider>,
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('ApiHealthCard', () => {
  it('shows loading and then the API status', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            data: {
              status: 'live',
              service: 'api',
              checked_at: '2026-08-30T00:00:00Z',
              dependencies: {},
            },
            meta: { request_id: 'request-123', cursor: null },
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        ),
      ),
    );

    renderCard();

    expect(screen.getByText('服务连接')).toBeInTheDocument();
    expect(await screen.findByText('API 存活')).toBeInTheDocument();
    expect(screen.getByText('请求标识：request-123')).toBeInTheDocument();
  });

  it('shows a retryable error state when the API cannot be reached', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('private network detail')));

    renderCard();

    expect(await screen.findByText('后端服务暂不可用')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '重试连接' })).toBeInTheDocument();
    expect(screen.queryByText('private network detail')).not.toBeInTheDocument();
  });
});