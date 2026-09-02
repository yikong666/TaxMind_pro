import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { FeedbackPage } from '@/pages/FeedbackPage';

describe('FeedbackPage', () => {
  it('shows virtual feedback item and internal-only boundary', () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter initialEntries={['/feedback?preview=1']}><FeedbackPage /></MemoryRouter>
      </QueryClientProvider>,
    );

    expect(screen.getByText('预览模式：仅展示虚构反馈')).toBeInTheDocument();
    expect(screen.getAllByText('citation_error').length).toBeGreaterThan(0);
    expect(screen.getByText('submitted')).toBeInTheDocument();
  });

  it('uses the compact feedback layout from the approved design', () => {
    render(<QueryClientProvider client={new QueryClient()}><MemoryRouter initialEntries={['/feedback?preview=1']}><FeedbackPage /></MemoryRouter></QueryClientProvider>);
    expect(screen.getByRole('heading', { name: '反馈纠错' })).toBeInTheDocument();
    expect(screen.getByText('处理动作在抽屉中完成，列表只保留关键状态')).toBeInTheDocument();
  });
});
