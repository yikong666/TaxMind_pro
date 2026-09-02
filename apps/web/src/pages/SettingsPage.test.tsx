import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { SettingsPage } from '@/pages/SettingsPage';

describe('SettingsPage', () => {
  it('renders members with preview writes disabled', () => {
    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <MemoryRouter initialEntries={['/settings?preview=1']}><SettingsPage /></MemoryRouter>
      </QueryClientProvider>,
    );

    expect(screen.getByRole('heading', { name: '设置' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '成员与权限' })).toBeInTheDocument();
    expect(screen.getByText('李敏')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '邀请成员' })).toBeDisabled();
  });
});
