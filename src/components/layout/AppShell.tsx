import type { ReactNode } from 'react';

interface AppShellProps {
  sidebar: ReactNode;
  topbar: ReactNode;
  children: ReactNode;
  sidebarCollapsed: boolean;
}

export function AppShell({ sidebar, topbar, children, sidebarCollapsed }: AppShellProps) {
  return (
    <div className={`app-shell ${sidebarCollapsed ? 'is-sidebar-collapsed' : ''}`}>
      {sidebar}
      <div className="app-shell__content">
        {topbar}
        <main className="main-content">{children}</main>
      </div>
    </div>
  );
}
