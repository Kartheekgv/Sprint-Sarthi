import { ArrowDownRight, ArrowUpRight, Minus } from 'lucide-react';
import { dashboardStats } from '../../data/dashboard';
import { AnalyticsIllustration } from '../common/DashboardIllustrations';

export function StatsGrid() {
  return (
    <section className="stats-grid" aria-label="Sprint metrics">
      <AnalyticsIllustration className="stats-grid__illustration" />
      {dashboardStats.map((stat) => {
        const Icon = stat.icon;
        return (
          <article className={`stat-card stat-card--${stat.tone}`} key={stat.label}>
            <div className="stat-card__top">
              <span className="stat-card__icon">
                <Icon size={21} />
              </span>
              <span
                className={`stat-card__trend stat-card__trend--${stat.trendDirection}`}
                title={stat.trend}
              >
                {stat.trendDirection === 'up' ? <ArrowUpRight size={14} /> : null}
                {stat.trendDirection === 'down' ? <ArrowDownRight size={14} /> : null}
                {stat.trendDirection === 'neutral' ? <Minus size={14} /> : null}
                {stat.trend}
              </span>
            </div>
            <div className="stat-card__value">{stat.value}</div>
            <h2>{stat.label}</h2>
            <p>{stat.helper}</p>
          </article>
        );
      })}
    </section>
  );
}
