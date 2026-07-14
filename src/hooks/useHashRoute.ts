import { useCallback, useEffect, useState } from 'react';
import type { RouteId } from '../types';

const validRoutes: RouteId[] = [
  'dashboard',
  'requirements',
  'planning',
  'backlog',
  'ai-suggestions',
  'documents',
  'jira',
  'team',
  'approvals',
  'reports',
  'activity',
  'settings',
  'members',
];

function readRoute(): RouteId {
  const value = window.location.hash.replace('#/', '') as RouteId;
  return validRoutes.includes(value) ? value : 'dashboard';
}

export function useHashRoute() {
  const [route, setRoute] = useState<RouteId>(readRoute);

  useEffect(() => {
    const onHashChange = () => setRoute(readRoute());
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);

  const navigate = useCallback((nextRoute: RouteId) => {
    const nextHash = `#/${nextRoute}`;
    if (window.location.hash === nextHash) {
      setRoute(nextRoute);
      return;
    }
    window.location.hash = nextHash;
  }, []);

  return { route, navigate };
}
