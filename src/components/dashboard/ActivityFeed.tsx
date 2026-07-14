import { ArrowRight } from 'lucide-react';
import { recentActivity } from '../../data/dashboard';
import type { RouteId } from '../../types';
import { Panel } from '../common/Panel';

interface ActivityFeedProps {
  onNavigate: (route: RouteId) => void;
}

export function ActivityFeed({ onNavigate }: ActivityFeedProps) {
  return (
    <Panel
      className="activity-feed"
      title="Recent activity"
      description="Important changes from your team and connected tools."
      action={
        <button className="text-action" onClick={() => onNavigate('activity')}>
          View all <ArrowRight size={15} />
        </button>
      }
    >
      <div className="activity-list">
        {recentActivity.map((activity) => {
          const Icon = activity.icon;
          return (
            <article className="activity-list__item" key={activity.id}>
              <span className={`activity-list__icon activity-list__icon--${activity.tone}`}>
                <Icon size={17} />
              </span>
              <div>
                <strong>{activity.title}</strong>
                <p>{activity.detail}</p>
                <time>{activity.time}</time>
              </div>
            </article>
          );
        })}
      </div>
    </Panel>
  );
}
