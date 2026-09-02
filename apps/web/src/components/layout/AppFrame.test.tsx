import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { AppFrame } from '@/components/layout/AppFrame';

describe('AppFrame', () => {
  it('renders the fixed TaxMind rail and page-specific top bar', () => {
    render(
      <MemoryRouter initialEntries={['/policies?preview=1']}>
        <Routes>
          <Route element={<AppFrame />}>
            <Route path="/policies" element={<div>政策页面内容</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByRole('navigation', { name: 'TaxMind 主导航' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'TaxMind' })).toHaveClass('app-rail-brand');
    expect(screen.getByRole('link', { name: '政策检索' })).toHaveClass('is-active');
    expect(screen.getByRole('banner')).toHaveTextContent('政策检索');
    expect(screen.getByText('当前项目：季度开票与优惠咨询')).toBeInTheDocument();
    expect(screen.getByText('政策页面内容')).toBeInTheDocument();
  });

  it('marks the 事项管理 entry active for its dedicated route', () => {
    render(
      <MemoryRouter initialEntries={['/cases/manage']}>
        <Routes>
          <Route element={<AppFrame />}>
            <Route path="/cases/manage" element={<div>事项页面内容</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByRole('link', { name: '事项管理' })).toHaveClass('is-active');
    expect(screen.getByRole('link', { name: '我的工作台' })).not.toHaveClass('is-active');
  });

  it('keeps preview mode when navigating between shell pages', () => {
    render(
      <MemoryRouter initialEntries={['/cases?preview=1']}>
        <Routes>
          <Route element={<AppFrame />}>
            <Route path="/cases" element={<div>工作台内容</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByRole('link', { name: '办税事项' })).toHaveAttribute(
      'href',
      '/procedures?preview=1',
    );
  });

  it('marks settings active and uses settings page metadata', () => {
    render(
      <MemoryRouter initialEntries={['/settings?preview=1']}>
        <Routes>
          <Route element={<AppFrame />}>
            <Route path="/settings" element={<div>设置页面内容</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByRole('link', { name: '设置' })).toHaveClass('is-active');
    expect(screen.getByRole('banner')).toHaveTextContent('设置');
    expect(screen.getByText('机构与成员')).toBeInTheDocument();
  });

  it('places the user avatar before settings in the bottom rail', () => {
    render(
      <MemoryRouter initialEntries={['/settings?preview=1']}>
        <Routes>
          <Route element={<AppFrame />}>
            <Route path="/settings" element={<div>设置页面内容</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    const bottomRail = document.querySelector('.app-rail-bottom');
    expect(bottomRail?.children[0]).toHaveAttribute('aria-label', '当前用户：李敏');
    expect(bottomRail?.children[1]).toHaveAttribute('aria-label', '设置');
  });
});
