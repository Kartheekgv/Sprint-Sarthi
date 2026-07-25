import {
  IconDashboard,
  IconRequirements,
  IconCalendar,
  IconBacklog,
  IconSparkle,
  IconDocuments,
  IconKanban,
  IconTeam,
  IconApprovals,
  IconReports,
  IconActivity,
  IconSettings,
  IconMembers,
  IconBot,
  IconGauge,
} from '../components/icons';
import type { NavigationGroup } from '../types';

export const navigationGroups: NavigationGroup[] = [
  {
    label: 'Workspace',
    items: [
      {
        id: 'dashboard',
        label: 'Dashboard',
        description: 'Sprint health and priorities',
        icon: IconDashboard,
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
        icon: IconRequirements,
        badge: 3,
      },
      {
        id: 'planning',
        label: 'Sprint planning',
        description: 'Scope and commit work',
        icon: IconCalendar,
      },
      {
        id: 'backlog',
        label: 'Backlog',
        description: 'Prioritise upcoming work',
        icon: IconBacklog,
        badge: 18,
      },
      {
        id: 'ai-suggestions',
        label: 'AI suggestions',
        description: 'Review planning insights',
        icon: IconSparkle,
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
        icon: IconDocuments,
      },
      {
        id: 'jira',
        label: 'Jira integration',
        description: 'Sync issues and projects',
        icon: IconKanban,
      },
      {
        id: 'team',
        label: 'Team and capacity',
        description: 'Availability and workload',
        icon: IconTeam,
      },
      {
        id: 'approvals',
        label: 'Approvals',
        description: 'Decisions waiting for review',
        icon: IconApprovals,
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
        icon: IconReports,
      },
      {
        id: 'activity',
        label: 'Activity log',
        description: 'Recent workspace changes',
        icon: IconActivity,
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
        icon: IconSettings,
      },
      {
        id: 'members',
        label: 'Members and roles',
        description: 'Access and permissions',
        icon: IconMembers,
      },
    ],
  },
];

export const routeLabels = Object.fromEntries(
  navigationGroups.flatMap((group) => group.items.map((item) => [item.id, item.label])),
) as Record<string, string>;

export const quickCreateItems = [
  { label: 'Create requirement', description: 'Capture a new product need', icon: IconRequirements },
  { label: 'Add backlog item', description: 'Create a work item for refinement', icon: IconBacklog },
  { label: 'Ask AI copilot', description: 'Get planning recommendations', icon: IconBot },
  { label: 'Review sprint health', description: 'Check readiness and risk', icon: IconGauge },
];
