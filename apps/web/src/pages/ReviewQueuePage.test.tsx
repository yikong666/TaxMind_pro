import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { ReviewQueuePage } from '@/pages/ReviewQueuePage';

describe('ReviewQueuePage', () => {
  it('shows a clearly labelled virtual review task with rule and fact gaps', () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter initialEntries={['/reviews?preview=1']}>
          <ReviewQueuePage />
        </MemoryRouter>
      </QueryClientProvider>,
    );
    expect(screen.getByText('预览模式：仅展示虚构审核任务')).toBeInTheDocument();
    expect(screen.getByText('规则：RISK-INVOICE-001-v1')).toBeInTheDocument();
    expect(screen.getByText('待补充：small_low_profit_status')).toBeInTheDocument();
  });

  it('uses the compact review queue layout from the approved design', () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter initialEntries={['/reviews?preview=1']}>
          <ReviewQueuePage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(screen.getByRole('heading', { name: '待审核' })).toBeInTheDocument();
    expect(screen.getByText('先处理风险与事实缺口，而不是展示大段摘要')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '审核' })).toBeInTheDocument();
  });
});
