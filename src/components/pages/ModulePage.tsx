import { ArrowRight, Filter, MoreHorizontal, Plus, Search, Sparkles } from 'lucide-react';
import { useMemo, useState } from 'react';
import type { ModulePageConfig, RouteId } from '../../types';
import { Button } from '../common/Button';
import { Panel } from '../common/Panel';
import { StatusBadge } from '../common/StatusBadge';

interface ModulePageProps {
  route: Exclude<RouteId, 'dashboard'>;
  config: ModulePageConfig;
  onPrimaryAction: (route: Exclude<RouteId, 'dashboard'>) => void;
}

const statuses = ['All statuses', 'Ready', 'In progress', 'Review', 'Pending', 'Blocked', 'Done'] as const;

export function ModulePage({ route, config, onPrimaryAction }: ModulePageProps) {
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState<(typeof statuses)[number]>('All statuses');

  const filteredRows = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return config.rows.filter((row) => {
      const matchesQuery =
        !normalizedQuery ||
        row.id.toLowerCase().includes(normalizedQuery) ||
        row.primary.toLowerCase().includes(normalizedQuery) ||
        row.secondary.toLowerCase().includes(normalizedQuery) ||
        row.owner.toLowerCase().includes(normalizedQuery);
      const matchesStatus = status === 'All statuses' || row.status === status;
      return matchesQuery && matchesStatus;
    });
  }, [config.rows, query, status]);

  return (
    <div className="module-page page-enter">
      <section className="module-hero">
        <div>
          <span className="module-hero__eyebrow">{config.eyebrow}</span>
          <h1>{config.title}</h1>
          <p>{config.description}</p>
        </div>
        <Button
          variant="primary"
          icon={<Plus size={17} />}
          trailingIcon={<ArrowRight size={16} />}
          onClick={() => onPrimaryAction(route)}
        >
          {config.primaryAction}
        </Button>
      </section>

      <section className="module-metrics" aria-label={`${config.title} metrics`}>
        {config.metrics.map((metric) => {
          const Icon = metric.icon;
          return (
            <article key={metric.label} className={`module-metric module-metric--${metric.tone}`}>
              <span className="module-metric__icon">
                <Icon size={20} />
              </span>
              <div>
                <small>{metric.label}</small>
                <strong>{metric.value}</strong>
                <p>{metric.detail}</p>
              </div>
            </article>
          );
        })}
      </section>

      <div className="module-content-grid">
        <Panel className="module-table-panel" padding="none">
          <div className="module-toolbar">
            <div>
              <h2>Workspace items</h2>
              <p>{filteredRows.length} of {config.rows.length} items shown</p>
            </div>
            <div className="module-toolbar__controls">
              <label className="table-search table-search--wide">
                <Search size={16} />
                <input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder={`Search ${config.title.toLowerCase()}`}
                />
              </label>
              <label className="filter-select">
                <Filter size={16} />
                <select value={status} onChange={(event) => setStatus(event.target.value as typeof status)}>
                  {statuses.map((option) => (
                    <option key={option}>{option}</option>
                  ))}
                </select>
              </label>
            </div>
          </div>

          {filteredRows.length ? (
            <div className="responsive-table module-table">
              <table>
                <thead>
                  <tr>
                    <th>Item</th>
                    <th>Owner</th>
                    <th>Status</th>
                    <th>Updated / target</th>
                    <th aria-label="Actions" />
                  </tr>
                </thead>
                <tbody>
                  {filteredRows.map((row) => (
                    <tr key={row.id}>
                      <td>
                        <div className="module-item-cell">
                          <span>{row.id}</span>
                          <div>
                            <strong>{row.primary}</strong>
                            <small>{row.secondary}</small>
                          </div>
                        </div>
                      </td>
                      <td>{row.owner}</td>
                      <td>
                        <StatusBadge status={row.status} />
                      </td>
                      <td>{row.date}</td>
                      <td>
                        <button className="icon-button" aria-label={`Actions for ${row.primary}`}>
                          <MoreHorizontal size={18} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="content-empty-state content-empty-state--large">
              <span>
                <Search size={25} />
              </span>
              <h3>No matching items</h3>
              <p>Change the search text or status filter to see more results.</p>
            </div>
          )}
        </Panel>

        <aside className="module-side-column">
          <Panel title="Recommended next steps" description="Practical guidance for this workspace.">
            <div className="tip-list">
              {config.tips.map((tip, index) => (
                <div className="tip-list__item" key={tip}>
                  <span>{index + 1}</span>
                  <p>{tip}</p>
                </div>
              ))}
            </div>
          </Panel>

          <Panel className="assistant-nudge">
            <span className="assistant-nudge__icon">
              <Sparkles size={21} />
            </span>
            <h2>Need a faster decision?</h2>
            <p>Ask the AI copilot to summarise this page, identify risk, or propose a practical next action.</p>
            <Button fullWidth trailingIcon={<ArrowRight size={16} />}>
              Open AI copilot
            </Button>
          </Panel>
        </aside>
      </div>
    </div>
  );
}
