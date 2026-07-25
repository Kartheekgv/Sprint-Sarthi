import { navigationGroups } from '../../data/navigation';
import type { RouteId } from '../../types';
import { Logo } from '../common/Logo';

interface SidebarProps {
  route: RouteId;
  collapsed: boolean;
  mobileOpen: boolean;
  onNavigate: (route: RouteId) => void;
  onCloseMobile: () => void;
}

export function Sidebar({
  route,
  collapsed,
  mobileOpen,
  onNavigate,
  onCloseMobile,
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
                        <Icon size={19} />
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
        </div>
      </aside>
    </>
  );
}
