import { FileText, MoreHorizontal, Search } from 'lucide-react';
import { useMemo, useState } from 'react';
import { recentInputs } from '../../data/dashboard';
import { Panel } from '../common/Panel';
import { StatusBadge } from '../common/StatusBadge';
import { KanbanIllustration } from '../common/DashboardIllustrations';

const tabs = ['Recent inputs', 'Meeting recordings', 'Notes and ideas', 'Descriptions'] as const;
type TabName = (typeof tabs)[number];

export function RecentWork() {
  const [activeTab, setActiveTab] = useState<TabName>('Recent inputs');
  const [query, setQuery] = useState('');

  const rows = useMemo(() => {
    if (activeTab !== 'Recent inputs') return [];
    const normalizedQuery = query.trim().toLowerCase();
    return recentInputs.filter((item) => item.name.toLowerCase().includes(normalizedQuery));
  }, [activeTab, query]);

  return (
    <Panel className="recent-work" padding="none">
      <KanbanIllustration className="recent-work__illustration" />
      <div className="recent-work__topbar">
        <div className="tab-list" role="tablist" aria-label="Recent project content">
          {tabs.map((tab) => (
            <button
              key={tab}
              className={activeTab === tab ? 'is-active' : ''}
              onClick={() => setActiveTab(tab)}
              role="tab"
              aria-selected={activeTab === tab}
            >
              {tab}
            </button>
          ))}
        </div>
        <label className="table-search">
          <Search size={16} />
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search inputs" />
        </label>
      </div>

      {rows.length ? (
        <div className="responsive-table">
          <table>
            <thead>
              <tr>
                <th>Input</th>
                <th>Owner</th>
                <th>Status</th>
                <th>Updated</th>
                <th aria-label="Actions" />
              </tr>
            </thead>
            <tbody>
              {rows.map((item) => (
                <tr key={item.id}>
                  <td>
                    <div className="table-primary-cell">
                      <span>
                        <FileText size={17} />
                      </span>
                      <div>
                        <strong>{item.name}</strong>
                        <small>{item.type}</small>
                      </div>
                    </div>
                  </td>
                  <td>{item.owner}</td>
                  <td>
                    <StatusBadge status={item.status} />
                  </td>
                  <td>{item.updated}</td>
                  <td>
                    <button className="icon-button" aria-label={`Actions for ${item.name}`}>
                      <MoreHorizontal size={18} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="content-empty-state">
          <span>
            <FileText size={25} />
          </span>
          <h3>{query ? 'No matching inputs' : `No ${activeTab.toLowerCase()} yet`}</h3>
          <p>{query ? 'Try a different search term.' : 'Add project context here when it becomes available.'}</p>
        </div>
      )}
    </Panel>
  );
}
