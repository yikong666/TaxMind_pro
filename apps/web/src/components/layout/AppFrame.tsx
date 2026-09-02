import {
  BadgeCheck,
  ClipboardList,
  Library,
  ListTodo,
  MessageSquare,
  Search,
  Settings,
} from 'lucide-react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';

import logoIcon from '../../../../../taxmind-logo-icon.svg';

interface NavigationItem {
  icon: typeof MessageSquare;
  label: string;
  to: string;
}

const navigationItems: NavigationItem[] = [
  { icon: MessageSquare, label: '我的工作台', to: '/cases' },
  { icon: ListTodo, label: '事项管理', to: '/cases/manage' },
  { icon: Search, label: '政策检索', to: '/policies' },
  { icon: ClipboardList, label: '办税事项', to: '/procedures' },
  { icon: BadgeCheck, label: '审核中心', to: '/reviews' },
  { icon: Library, label: '知识运营', to: '/knowledge' },
];

function pageMeta(pathname: string) {
  if (pathname.startsWith('/policies')) {
    return { title: '政策检索', subtitle: '当前项目：季度开票与优惠咨询' };
  }
  if (pathname.startsWith('/cases/manage')) {
    return { title: '事项管理', subtitle: '项目概览与处理进度' };
  }
  if (pathname.startsWith('/procedures')) {
    return { title: '办税事项', subtitle: '地区化流程和材料' };
  }
  if (pathname.startsWith('/reviews')) {
    return { title: '审核中心', subtitle: '复核负责人' };
  }
  if (pathname.startsWith('/knowledge')) {
    return { title: '知识运营', subtitle: '知识管理员' };
  }
  if (pathname.startsWith('/feedback')) {
    return { title: '反馈纠错', subtitle: '质量与合规' };
  }
  if (pathname.startsWith('/audit')) {
    return { title: '操作审计', subtitle: '仅限授权审计角色' };
  }
  if (pathname.startsWith('/settings')) {
    return { title: '设置', subtitle: '机构与成员' };
  }
  return { title: '我的工作台', subtitle: '专业事项与智能问答' };
}

export function AppFrame() {
  const location = useLocation();
  const meta = pageMeta(location.pathname);
  const isPreview = new URLSearchParams(location.search).get('preview') === '1';
  const isNavigationItemActive = (to: string) => {
    if (to === '/cases') return location.pathname === '/cases';
    return location.pathname.startsWith(to);
  };

  return (
    <div className="app-frame">
      <aside className="app-rail">
        <nav aria-label="TaxMind 主导航">
          <NavLink aria-label="TaxMind" className="app-rail-brand" to="/cases">
            <img alt="" src={logoIcon} />
            <span>TaxMind</span>
          </NavLink>
          <div className="app-rail-actions">
            {navigationItems.map(({ icon: Icon, label, to }) => {
              const routeTo = isPreview ? `${to}${to.includes('?') ? '&' : '?'}preview=1` : to;

              return (
                <NavLink
                  className={`app-rail-btn ${isNavigationItemActive(to) ? 'is-active' : ''}`}
                  key={label}
                  to={routeTo}
                >
                  <Icon aria-hidden="true" size={17} strokeWidth={1.8} />
                  <span>{label}</span>
                </NavLink>
              );
            })}
          </div>
        </nav>
        <div className="app-rail-bottom">
          <span aria-label="当前用户：李敏" className="app-avatar">
            李
          </span>
          <NavLink
            aria-label="设置"
            className={`app-rail-btn ${location.pathname.startsWith('/settings') ? 'is-active' : ''}`}
            to={isPreview ? '/settings?preview=1' : '/settings'}
          >
            <Settings aria-hidden="true" size={17} strokeWidth={1.8} />
            <span>设置</span>
          </NavLink>
        </div>
      </aside>
      <section className="app-frame-page">
        <header className="app-topbar">
          <div className="app-topbar-left">
            <span className="app-topbar-title">{meta.title}</span>
            <span className="app-topbar-subtitle">{meta.subtitle}</span>
          </div>
        </header>
        <div className="app-frame-outlet">
          <Outlet />
        </div>
      </section>
    </div>
  );
}
