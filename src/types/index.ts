import type { ComponentType, SVGProps } from 'react';

export type IconComponent = ComponentType<SVGProps<SVGSVGElement> & { size?: number }>;

export type ThemeMode = 'dark' | 'light';

export type RouteId =
  | 'dashboard'
  | 'requirements'
  | 'planning'
  | 'backlog'
  | 'ai-suggestions'
  | 'documents'
  | 'jira'
  | 'team'
  | 'approvals'
  | 'reports'
  | 'activity'
  | 'settings'
  | 'members';

export interface NavigationItem {
  id: RouteId;
  label: string;
  description: string;
  icon: IconComponent;
  badge?: number | string;
}

export interface NavigationGroup {
  label: string;
  items: NavigationItem[];
}

export interface SprintDraft {
  name: string;
  objective: string;
  productArea: string;
  owner: string;
  team: string;
  duration: string;
  capacity: string;
  priority: 'Low' | 'Medium' | 'High' | 'Critical';
  dependencies: string;
  risks: string;
  definitionOfDone: string;
}

export interface QueuedFile {
  id: string;
  name: string;
  size: number;
  type: string;
  addedAt: string;
}

export interface ToastMessage {
  id: string;
  title: string;
  message?: string;
  tone: 'success' | 'info' | 'warning' | 'danger';
}

export interface StatItem {
  label: string;
  value: string;
  helper: string;
  trend: string;
  trendDirection: 'up' | 'down' | 'neutral';
  icon: LucideIcon;
  tone: 'violet' | 'blue' | 'green' | 'orange' | 'pink';
}

export interface ActivityItem {
  id: string;
  title: string;
  detail: string;
  time: string;
  icon: LucideIcon;
  tone: 'violet' | 'blue' | 'green' | 'orange';
}

export interface ChatMessage {
  id: string;
  role: 'assistant' | 'user';
  text: string;
  timestamp: string;
}

export interface ModuleMetric {
  label: string;
  value: string;
  detail: string;
  icon: LucideIcon;
  tone: 'violet' | 'blue' | 'green' | 'orange';
}

export interface ModuleRow {
  id: string;
  primary: string;
  secondary: string;
  owner: string;
  status: 'Ready' | 'In progress' | 'Blocked' | 'Review' | 'Done' | 'Pending';
  date: string;
}

export interface ModulePageConfig {
  eyebrow: string;
  title: string;
  description: string;
  primaryAction: string;
  metrics: ModuleMetric[];
  rows: ModuleRow[];
  tips: string[];
}
