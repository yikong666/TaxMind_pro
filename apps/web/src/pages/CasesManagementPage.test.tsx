import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { CasesManagementPage } from '@/pages/CasesManagementPage';

describe('CasesManagementPage', () => {
  it('renders the compact project table and opens the selected item in the workbench', () => {
    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <MemoryRouter initialEntries={['/cases/manage?preview=1']}>
          <Routes>
            <Route path="/cases/manage" element={<CasesManagementPage />} />
            <Route path="/cases" element={<div>工作台目标页</div>} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(screen.getByRole('heading', { name: '我的事项' })).toBeInTheDocument();
    expect(screen.getByText('季度开票与优惠咨询')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '继续处理季度开票与优惠咨询' }));
    expect(screen.getByText('工作台目标页')).toBeInTheDocument();
  });
});
