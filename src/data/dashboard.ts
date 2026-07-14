import {
  AlertTriangle,
  CheckCircle2,
  ClipboardList,
  FileCheck2,
  Gauge,
  GitPullRequestArrow,
  Sparkles,
  TimerReset,
  UsersRound,
} from 'lucide-react';
import type { ActivityItem, StatItem } from '../types';

export const dashboardStats: StatItem[] = [
  {
    label: 'Sprint progress',
    value: '68%',
    helper: '26 of 38 points complete',
    trend: '+12% this week',
    trendDirection: 'up',
    icon: Gauge,
    tone: 'violet',
  },
  {
    label: 'Work items',
    value: '42',
    helper: '8 currently in progress',
    trend: '4 added today',
    trendDirection: 'neutral',
    icon: ClipboardList,
    tone: 'blue',
  },
  {
    label: 'Completed',
    value: '26',
    helper: '62% of committed items',
    trend: '+5 since Monday',
    trendDirection: 'up',
    icon: CheckCircle2,
    tone: 'green',
  },
  {
    label: 'Capacity used',
    value: '81%',
    helper: '194 of 240 team hours',
    trend: 'Healthy range',
    trendDirection: 'neutral',
    icon: UsersRound,
    tone: 'orange',
  },
  {
    label: 'AI recommendations',
    value: '7',
    helper: '3 high-impact actions',
    trend: '2 new suggestions',
    trendDirection: 'up',
    icon: Sparkles,
    tone: 'pink',
  },
];

export const recentActivity: ActivityItem[] = [
  {
    id: 'a1',
    title: 'Requirement approved',
    detail: 'Fleet health alert workflow was approved by Priya.',
    time: '12 minutes ago',
    icon: FileCheck2,
    tone: 'green',
  },
  {
    id: 'a2',
    title: 'Jira sync completed',
    detail: '14 updated issues were imported from CLOUD-OPS.',
    time: '38 minutes ago',
    icon: GitPullRequestArrow,
    tone: 'blue',
  },
  {
    id: 'a3',
    title: 'Capacity risk detected',
    detail: 'Backend capacity may exceed the recommended threshold.',
    time: '1 hour ago',
    icon: AlertTriangle,
    tone: 'orange',
  },
  {
    id: 'a4',
    title: 'Sprint estimate updated',
    detail: 'The forecast moved from 34 to 38 story points.',
    time: 'Yesterday',
    icon: TimerReset,
    tone: 'violet',
  },
];

export const recentInputs = [
  {
    id: 'r1',
    name: 'Fleet health dashboard brief',
    type: 'Requirement',
    owner: 'Kartheek Reddy',
    updated: '18 minutes ago',
    status: 'Ready' as const,
  },
  {
    id: 'r2',
    name: 'Customer interview synthesis',
    type: 'Research notes',
    owner: 'Maya Singh',
    updated: '2 hours ago',
    status: 'Review' as const,
  },
  {
    id: 'r3',
    name: 'API dependency map',
    type: 'Document',
    owner: 'Anders Lind',
    updated: 'Yesterday',
    status: 'Draft' as const,
  },
];
