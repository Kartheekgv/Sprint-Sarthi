import {
  Activity,
  BarChart3,
  Bot,
  CalendarRange,
  ClipboardCheck,
  FileStack,
  Gauge,
  SquareKanban,
  LayoutDashboard,
  ListTodo,
  Settings,
  ShieldCheck,
  Sparkles,
  UsersRound,
} from 'lucide-react';
import type { NavigationGroup } from '../types';

export const navigationGroups: NavigationGroup[] = [
  {
    label: 'Workspace',
    items: [
      {
        id: 'dashboard',
        label: 'Dashboard',
        description: 'Sprint health and priorities',
        icon: LayoutDashboard,
      },
    ],
  },
  {
    label: 'Plan',
    items: [
      {
        id: 'requirements',
        label: 'Requirements',
        description: 'Capture goals and context',
        icon: ShieldCheck,
        badge: 3,
      },
      {
        id: 'planning',
        label: 'Sprint planning',
        description: 'Scope and commit work',
        icon: CalendarRange,
      },
      {
        id: 'backlog',
        label: 'Backlog',
        description: 'Prioritise upcoming work',
        icon: ListTodo,
        badge: 18,
      },
      {
        id: 'ai-suggestions',
        label: 'AI suggestions',
        description: 'Review planning insights',
        icon: Sparkles,
        badge: 7,
      },
    ],
  },
  {
    label: 'Deliver',
    items: [
      {
        id: 'documents',
        label: 'Documents',
        description: 'Files, notes and recordings',
        icon: FileStack,
      },
      {
        id: 'jira',
        label: 'Jira integration',
        description: 'Sync issues and projects',
        icon: SquareKanban,
      },
      {
        id: 'team',
        label: 'Team and capacity',
        description: 'Availability and workload',
        icon: UsersRound,
      },
      {
        id: 'approvals',
        label: 'Approvals',
        description: 'Decisions waiting for review',
        icon: ClipboardCheck,
        badge: 2,
      },
    ],
  },
  {
    label: 'Insights',
    items: [
      {
        id: 'reports',
        label: 'Reports',
        description: 'Velocity and delivery trends',
        icon: BarChart3,
      },
      {
        id: 'activity',
        label: 'Activity log',
        description: 'Recent workspace changes',
        icon: Activity,
      },
    ],
  },
  {
    label: 'Administration',
    items: [
      {
        id: 'settings',
        label: 'Settings',
        description: 'Workspace preferences',
        icon: Settings,
      },
      {
        id: 'members',
        label: 'Members and roles',
        description: 'Access and permissions',
        icon: UsersRound,
      },
    ],
  },
];

export const routeLabels = Object.fromEntries(
  navigationGroups.flatMap((group) => group.items.map((item) => [item.id, item.label])),
) as Record<string, string>;

export const quickCreateItems = [
  { label: 'Create requirement', description: 'Capture a new product need', icon: ShieldCheck },
  { label: 'Add backlog item', description: 'Create a work item for refinement', icon: ListTodo },
  { label: 'Ask AI copilot', description: 'Get planning recommendations', icon: Bot },
  { label: 'Review sprint health', description: 'Check readiness and risk', icon: Gauge },
];
