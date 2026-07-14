import { ArrowRight, Search } from 'lucide-react';
import { useMemo, useState } from 'react';
import { navigationGroups } from '../../data/navigation';
import type { RouteId } from '../../types';
import { Modal } from './Modal';

interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
  onNavigate: (route: RouteId) => void;
}

export function CommandPalette({ open, onClose, onNavigate }: CommandPaletteProps) {
  const [query, setQuery] = useState('');
  const items = useMemo(() => navigationGroups.flatMap((group) => group.items), []);
  const filteredItems = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    if (!normalizedQuery) return items;
    return items.filter(
      (item) =>
        item.label.toLowerCase().includes(normalizedQuery) ||
        item.description.toLowerCase().includes(normalizedQuery),
    );
  }, [items, query]);

  const selectItem = (route: RouteId) => {
    onNavigate(route);
    setQuery('');
    onClose();
  };

  return (
    <Modal open={open} onClose={onClose} title="Go anywhere" description="Search pages and workspace tools." size="sm">
      <div className="command-search">
        <Search size={18} />
        <input
          autoFocus
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search dashboard, backlog, reports..."
        />
        <kbd>Esc</kbd>
      </div>
      <div className="command-results">
        {filteredItems.length ? (
          filteredItems.map((item) => {
            const Icon = item.icon;
            return (
              <button key={item.id} onClick={() => selectItem(item.id)}>
                <span className="command-results__icon">
                  <Icon size={18} />
                </span>
                <span>
                  <strong>{item.label}</strong>
                  <small>{item.description}</small>
                </span>
                <ArrowRight size={17} />
              </button>
            );
          })
        ) : (
          <div className="empty-inline">No matching page found.</div>
        )}
      </div>
    </Modal>
  );
}
