import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { KnowledgeOperationsPage } from '@/pages/KnowledgeOperationsPage';

describe('KnowledgeOperationsPage', () => {
  it('renders the candidate review panel and publish-batch boundary in preview mode', () => {
    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <MemoryRouter initialEntries={['/knowledge?preview=1']}>
          <KnowledgeOperationsPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(screen.getByRole('heading', { name: '知识运营' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '待审核候选' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '当前发布批次' })).toBeInTheDocument();
    expect(screen.getByText('第一条：适用范围')).toBeInTheDocument();
  });
});
