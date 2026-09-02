import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { SettingsPage } from '@/pages/SettingsPage';

describe('SettingsPage', () => {
  it('shows a clear unavailable state instead of a broken settings route', () => {
    render(<MemoryRouter initialEntries={['/settings?preview=1']}><SettingsPage /></MemoryRouter>);
    expect(screen.getByRole('heading', { name: '设置' })).toBeInTheDocument();
    expect(screen.getByText('成员和机构设置尚未接入当前 MVP API。')).toBeInTheDocument();
  });
});
