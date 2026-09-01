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
    expect(screen.getByText('citation_error')).toBeInTheDocument();
    expect(screen.getByText('submitted')).toBeInTheDocument();
  });
});
