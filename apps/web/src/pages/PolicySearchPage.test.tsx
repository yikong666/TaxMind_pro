import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { PolicySearchPage } from '@/pages/PolicySearchPage';

describe('PolicySearchPage', () => {
  it('opens a clause-level evidence drawer without treating a national fallback as local guidance', () => {
    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <MemoryRouter initialEntries={['/policies?preview=1']}>
          <PolicySearchPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    fireEvent.click(screen.getByRole('button', { name: '查看' }));

    const drawer = screen.getByRole('dialog', { name: '条款证据详情' });
    expect(drawer).toBeInTheDocument();
    expect(
      within(drawer).getByText('这是用于界面预览的虚构条款，不构成政策依据或专业结论。'),
    ).toBeInTheDocument();
    expect(within(drawer).getByText('TEST-2026-001')).toBeInTheDocument();
    expect(within(drawer).getByText('全国口径回退')).toBeInTheDocument();
    expect(within(drawer).getByRole('link', { name: '官方公开来源' })).toHaveAttribute(
      'href',
      'https://example.invalid/virtual-policy',
    );
  });

  it('uses the compact evidence-search layout from the approved design', () => {
    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <MemoryRouter initialEntries={['/policies?preview=1']}>
          <PolicySearchPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(screen.getByRole('heading', { name: '查找政策证据' })).toBeInTheDocument();
    expect(screen.getByText('搜索、筛选和证据详情保持在一个轻量页面中')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '查看' })).toBeInTheDocument();
  });
});
