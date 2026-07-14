import { AlertTriangle, ArrowUpRight, CheckCircle2, Clock3, MoreHorizontal } from 'lucide-react';
import { Panel } from '../common/Panel';
import { ProgressRing } from '../common/ProgressRing';

const burnValues = [42, 39, 35, 33, 28, 25, 20, 18, 13, 9];

export function SprintPulse() {
  return (
    <Panel
      className="sprint-pulse"
      title="Sprint pulse"
      description="Progress, forecast, and the risks that need attention."
      action={
        <button className="icon-button" aria-label="More sprint pulse options">
          <MoreHorizontal size={19} />
        </button>
      }
    >
      <div className="pulse-overview">
        <ProgressRing value={68} label="68%" helper="complete" />
        <div className="pulse-overview__copy">
          <span className="forecast-pill">
            <ArrowUpRight size={14} /> On track
          </span>
          <strong>Forecast: 36 of 38 points</strong>
          <p>The team is likely to complete 95% of the committed sprint scope.</p>
        </div>
      </div>

      <div className="burndown-mini">
        <div className="burndown-mini__header">
          <div>
            <strong>Burndown trend</strong>
            <small>Remaining story points</small>
          </div>
          <span>Day 6 of 10</span>
        </div>
        <div className="burndown-mini__chart" aria-label="Burndown chart">
          <div className="chart-gridline chart-gridline--one" />
          <div className="chart-gridline chart-gridline--two" />
          {burnValues.map((value, index) => (
            <span
              key={`${value}-${index}`}
              className={`chart-bar ${index < 6 ? 'is-elapsed' : ''}`}
              style={{ height: `${Math.max(14, (value / 42) * 100)}%` }}
              title={`Day ${index + 1}: ${value} points remaining`}
            />
          ))}
        </div>
      </div>

      <div className="pulse-checks">
        <div className="pulse-check pulse-check--success">
          <span>
            <CheckCircle2 size={17} />
          </span>
          <div>
            <strong>Scope is stable</strong>
            <small>No unplanned items added in 48 hours.</small>
          </div>
        </div>
        <div className="pulse-check pulse-check--warning">
          <span>
            <AlertTriangle size={17} />
          </span>
          <div>
            <strong>Backend allocation at 91%</strong>
            <small>Consider moving one five-point item.</small>
          </div>
        </div>
        <div className="pulse-check">
          <span>
            <Clock3 size={17} />
          </span>
          <div>
            <strong>One approval due today</strong>
            <small>Sprint scope needs product approval.</small>
          </div>
        </div>
      </div>
    </Panel>
  );
}
