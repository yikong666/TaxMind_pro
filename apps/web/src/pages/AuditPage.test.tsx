import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { AuditPage } from '@/pages/AuditPage';

describe('AuditPage', () => {
  it('shows virtual safe audit entries without raw before or after payloads', () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter initialEntries={['/audit?preview=1']}><AuditPage /></MemoryRouter>
      </QueryClientProvider>,
    );

    expect(screen.getByText('预览模式：仅展示虚构审计记录')).toBeInTheDocument();
    expect(screen.getByText('review.task.action_recorded')).toBeInTheDocument();
    expect(screen.queryByText('before_json')).not.toBeInTheDocument();
  });
});
