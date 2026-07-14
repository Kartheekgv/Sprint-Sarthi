import {
  ChevronDown,
  LogOut,
  Menu,
  Moon,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  Sun,
  X,
} from 'lucide-react';
import { navigationGroups } from '../../data/navigation';
import type { RouteId, ThemeMode } from '../../types';
import { Avatar } from '../common/Avatar';
import { Logo } from '../common/Logo';

interface SidebarProps {
  route: RouteId;
  collapsed: boolean;
  mobileOpen: boolean;
  theme: ThemeMode;
  onNavigate: (route: RouteId) => void;
  onToggleCollapsed: () => void;
  onCloseMobile: () => void;
  onToggleTheme: () => void;
  onNewSprint: () => void;
}

export function Sidebar({
  route,
  collapsed,
  mobileOpen,
  theme,
  onNavigate,
  onToggleCollapsed,
  onCloseMobile,
  onToggleTheme,
  onNewSprint,
}: SidebarProps) {
  const navigate = (nextRoute: RouteId) => {
    onNavigate(nextRoute);
    onCloseMobile();
  };

  return (
    <>
      <button
        className={`sidebar-scrim ${mobileOpen ? 'is-visible' : ''}`}
        onClick={onCloseMobile}
        aria-label="Close navigation"
        tabIndex={mobileOpen ? 0 : -1}
      />
      <aside
        className={`sidebar ${collapsed ? 'is-collapsed' : ''} ${mobileOpen ? 'is-mobile-open' : ''}`}
        aria-label="Primary navigation"
      >
        <div className="sidebar__topbar">
          <Logo compact={collapsed} />
          <button
            className="sidebar__desktop-toggle icon-button"
            onClick={onToggleCollapsed}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? <PanelLeftOpen size={19} /> : <PanelLeftClose size={19} />}
          </button>
          <button className="sidebar__mobile-close icon-button" onClick={onCloseMobile} aria-label="Close navigation">
            <X size={20} />
          </button>
        </div>

        <div className="sidebar__workspace">
          <button className="workspace-switcher" title={collapsed ? 'Cloud Operations' : undefined}>
            <span className="workspace-switcher__icon">CO</span>
            {!collapsed ? (
              <>
                <span className="workspace-switcher__copy">
                  <small>Workspace</small>
                  <strong>Cloud Operations</strong>
                </span>
                <ChevronDown size={16} />
              </>
            ) : null}
          </button>

          <button
            className={`sidebar-create ${collapsed ? 'sidebar-create--compact' : ''}`}
            onClick={onNewSprint}
            title={collapsed ? 'Create new sprint' : undefined}
          >
            <Plus size={18} />
            {!collapsed ? <span>New sprint</span> : null}
          </button>
        </div>

        <nav className="sidebar__nav">
          {navigationGroups.map((group) => (
            <div className="nav-group" key={group.label}>
              {!collapsed ? <p className="nav-group__label">{group.label}</p> : <span className="nav-group__separator" />}
              <div className="nav-group__items">
                {group.items.map((item) => {
                  const Icon = item.icon;
                  const active = route === item.id;
                  return (
                    <button
                      key={item.id}
                      className={`nav-item ${active ? 'is-active' : ''}`}
                      onClick={() => navigate(item.id)}
                      title={collapsed ? `${item.label} - ${item.description}` : undefined}
                      aria-current={active ? 'page' : undefined}
                    >
                      <span className="nav-item__icon">
                        <Icon size={19} strokeWidth={2} />
                      </span>
                      {!collapsed ? (
                        <span className="nav-item__copy">
                          <strong>{item.label}</strong>
                          <small>{item.description}</small>
                        </span>
                      ) : null}
                      {item.badge ? <span className="nav-item__badge">{item.badge}</span> : null}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>

        <div className="sidebar__footer">
          {!collapsed ? (
            <div className="readiness-card">
              <div className="readiness-card__header">
                <span>Planning readiness</span>
                <strong>82%</strong>
              </div>
              <div className="readiness-card__bar" aria-label="Planning readiness 82 percent">
                <span style={{ width: '82%' }} />
              </div>
              <p>Two items need attention before commitment.</p>
              <button onClick={() => navigate('planning')}>Review readiness</button>
            </div>
          ) : null}

          <button className="theme-toggle" onClick={onToggleTheme} title={collapsed ? 'Toggle theme' : undefined}>
            <span>{theme === 'dark' ? <Moon size={18} /> : <Sun size={18} />}</span>
            {!collapsed ? (
              <>
                <span className="theme-toggle__copy">
                  <strong>{theme === 'dark' ? 'Dark mode' : 'Light mode'}</strong>
                  <small>Change appearance</small>
                </span>
                <span className={`switch ${theme === 'dark' ? 'is-on' : ''}`} aria-hidden="true">
                  <span />
                </span>
              </>
            ) : null}
          </button>

          <button className="profile-card" title={collapsed ? 'Kartheek Reddy' : undefined}>
            <Avatar name="Kartheek Reddy" size="md" online />
            {!collapsed ? (
              <>
                <span className="profile-card__copy">
                  <strong>Kartheek Reddy</strong>
                  <small>Workspace admin</small>
                </span>
                <Menu size={17} />
              </>
            ) : null}
          </button>

          {!collapsed ? (
            <button className="sidebar-signout">
              <LogOut size={16} />
              <span>Sign out</span>
            </button>
          ) : null}
        </div>
      </aside>
    </>
  );
}
