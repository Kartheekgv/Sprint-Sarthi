type Status = 'Ready' | 'In progress' | 'Blocked' | 'Review' | 'Done' | 'Pending' | 'Draft';

interface StatusBadgeProps {
  status: Status;
}

const statusClass: Record<Status, string> = {
  Ready: 'status-badge--ready',
  'In progress': 'status-badge--progress',
  Blocked: 'status-badge--blocked',
  Review: 'status-badge--review',
  Done: 'status-badge--done',
  Pending: 'status-badge--pending',
  Draft: 'status-badge--draft',
};

export function StatusBadge({ status }: StatusBadgeProps) {
  return <span className={`status-badge ${statusClass[status]}`}>{status}</span>;
}
