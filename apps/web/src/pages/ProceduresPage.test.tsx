import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { ProceduresPage } from '@/pages/ProceduresPage';

describe('ProceduresPage', () => {
  it('shows a clearly marked virtual procedure with materials and official source link', () => {
    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <MemoryRouter initialEntries={['/procedures?preview=1']}>
          <ProceduresPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(screen.getByText('预览模式：仅展示虚构办税事项')).toBeInTheDocument();
    expect(screen.getByText('虚构红字发票开具指引')).toBeInTheDocument();
    expect(screen.getByText('材料：虚构材料清单')).toBeInTheDocument();
    expect(screen.getByText('本地地区匹配')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '官方办理入口' })).toHaveAttribute(
      'href',
      'https://example.invalid/procedure',
    );
  });

  it('uses the compact procedure list layout from the approved design', () => {
    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <MemoryRouter initialEntries={['/procedures?preview=1']}>
          <ProceduresPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(screen.getByRole('heading', { name: '办税事项' })).toBeInTheDocument();
    expect(screen.getByText('把材料、渠道和官方入口聚合在单个清爽列表')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '详情' })).toBeInTheDocument();
  });
});
