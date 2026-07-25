import {
  Bell,
  CheckCircle2,
  ChevronDown,
  Command,
  LogOut,
  Menu,
  Moon,
  RefreshCw,
  Search,
  Settings,
  Sun,
  UserRound,
} from 'lucide-react';
import { useCallback, useRef, useState } from 'react';
import { routeLabels } from '../../data/navigation';
import { useOutsideClick } from '../../hooks/useOutsideClick';
import type { RouteId, ThemeMode } from '../../types';
import { Avatar } from '../common/Avatar';
import { Button } from '../common/Button';

interface TopbarProps {
  route: RouteId;
  selectedProject: string;
  isSyncing: boolean;
  theme: ThemeMode;
  onProjectChange: (project: string) => void;
  onToggleSidebar: () => void;
  onOpenCommand: () => void;
  onSync: () => void;
  onNavigate: (route: RouteId) => void;
  onToggleTheme: () => void;
  onLogout: () => void;
}

const notifications = [
  { title: 'Approval requested', detail: 'Sprint 24 scope is waiting for your review.', time: '8 min' },
  { title: 'Capacity risk detected', detail: 'Backend allocation is above 90%.', time: '42 min' },
  { title: 'Jira sync completed', detail: '14 work items were updated.', time: '1 hr' },
];

export function Topbar({
  route,
  selectedProject,
  isSyncing,
  theme,
  onProjectChange,
  onToggleSidebar,
  onOpenCommand,
  onSync,
  onNavigate,
  onToggleTheme,
  onLogout,
}: TopbarProps) {
  const [notificationOpen, setNotificationOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const notificationRef = useRef<HTMLDivElement>(null);
  const profileRef = useRef<HTMLDivElement>(null);

  const closeNotifications = useCallback(() => setNotificationOpen(false), []);
  const closeProfile = useCallback(() => setProfileOpen(false), []);
  useOutsideClick(notificationRef, closeNotifications, notificationOpen);
  useOutsideClick(profileRef, closeProfile, profileOpen);

  return (
    <header className="topbar">
      <div className="topbar__title-group">
        <button className="topbar__sidebar-toggle icon-button" onClick={onToggleSidebar} aria-label="Toggle sidebar">
          <Menu size={21} />
        </button>
        <div className="topbar__breadcrumb">
          <span>Cloud Operations</span>
          <small>/</small>
          <strong>{routeLabels[route]}</strong>
        </div>
      </div>

      <div className="topbar__actions">
        <button className="global-search" onClick={onOpenCommand}>
          <Search size={17} />
          <span>Search workspace</span>
          <kbd>
            <Command size={12} /> K
          </kbd>
        </button>

        <Button
          className="topbar__sync"
          icon={<RefreshCw className={isSyncing ? 'is-spinning' : ''} size={17} />}
          onClick={onSync}
          disabled={isSyncing}
        >
          {isSyncing ? 'Syncing...' : 'Sync Jira'}
        </Button>

        <label className="project-select" aria-label="Select project">
          <span className="project-select__dot" />
          <select value={selectedProject} onChange={(event) => onProjectChange(event.target.value)}>
            <option>Cloud Operations</option>
            <option>Fleet Experience</option>
            <option>Customer Portal</option>
          </select>
          <ChevronDown size={15} />
        </label>

        <div className="topbar-popover" ref={notificationRef}>
          <button
            className="notification-button icon-button"
            onClick={() => setNotificationOpen((current) => !current)}
            aria-label="Open notifications"
            aria-expanded={notificationOpen}
          >
            <Bell size={19} />
            <span className="notification-button__count">3</span>
          </button>
          {notificationOpen ? (
            <div className="popover popover--notifications">
              <div className="popover__header">
                <div>
                  <strong>Notifications</strong>
                  <small>Three unread updates</small>
                </div>
                <button>Mark all read</button>
              </div>
              <div className="notification-list">
                {notifications.map((notification) => (
                  <button key={notification.title} className="notification-item">
                    <span className="notification-item__icon">
                      <CheckCircle2 size={17} />
                    </span>
                    <span>
                      <strong>{notification.title}</strong>
                      <small>{notification.detail}</small>
                    </span>
                    <time>{notification.time}</time>
                  </button>
                ))}
              </div>
              <button className="popover__footer" onClick={() => onNavigate('activity')}>
                View activity log
              </button>
            </div>
          ) : null}
        </div>

        <div className="topbar-popover" ref={profileRef}>
          <button
            className="topbar-profile"
            onClick={() => setProfileOpen((current) => !current)}
            aria-expanded={profileOpen}
          >
            <Avatar name="Kartheek Reddy" size="sm" online />
            <span>Kartheek</span>
            <ChevronDown size={15} />
          </button>
          {profileOpen ? (
            <div className="popover popover--profile">
              <div className="profile-summary">
                <Avatar name="Kartheek Reddy" size="md" online />
                <div>
                  <strong>Kartheek Reddy</strong>
                  <small>kartheek.reddy@example.com</small>
                </div>
              </div>
              <button onClick={onToggleTheme} className="profile-menu-item">
                {theme === 'dark' ? <Moon size={17} /> : <Sun size={17} />}
                {theme === 'dark' ? 'Dark mode' : 'Light mode'}
                <span className={`switch ${theme === 'dark' ? 'is-on' : ''}`} aria-hidden="true"><span /></span>
              </button>
              <button onClick={() => onNavigate('settings')} className="profile-menu-item">
                <Settings size={17} /> Settings
              </button>
              <button className="profile-menu-item">
                <UserRound size={17} /> Profile
              </button>
              <div className="profile-divider" />
              <button onClick={onLogout} className="profile-menu-item profile-menu-item--danger">
                <LogOut size={17} /> Sign out
              </button>
            </div>
          ) : null}
        </div>
      </div>
    </header>
  );
}
