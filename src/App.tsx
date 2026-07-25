import { useEffect, useState } from 'react';
import { CommandPalette } from './components/common/CommandPalette';
import { NewSprintModal } from './components/common/NewSprintModal';
import { ToastStack } from './components/common/ToastStack';
import { AppShell } from './components/layout/AppShell';
import { Sidebar } from './components/layout/Sidebar';
import { Topbar } from './components/layout/Topbar';
import { DashboardPage } from './components/pages/DashboardPage';
import { LoginPage } from './components/pages/LoginPage';
import { ModulePage } from './components/pages/ModulePage';
import { modulePages } from './data/modulePages';
import { useAuth } from './hooks/useAuth';
import { useHashRoute } from './hooks/useHashRoute';
import { useLocalStorage } from './hooks/useLocalStorage';
import { useToast } from './hooks/useToast';
import { createSprint, saveSprintDraft, syncWithJira } from './services/mockApi';
import type { QueuedFile, SprintDraft, ThemeMode } from './types';

const initialDraft: SprintDraft = {
  name: 'Cloud Operations Sprint 25',
  objective: 'Reduce avoidable service incidents by improving telemetry ingestion resilience and operational visibility.',
  productArea: 'Cloud Operations',
  owner: 'Kartheek Reddy',
  team: 'Cloud Platform',
  duration: '10',
  capacity: '240',
  priority: 'High',
  dependencies: '',
  risks: '',
  definitionOfDone: 'The selected work is deployed, monitored, documented, and accepted by the product owner.',
};

const initialFiles: QueuedFile[] = [
  {
    id: 'demo-file',
    name: 'sprint-25-planning-brief.pdf',
    size: 2_860_000,
    type: 'application/pdf',
    addedAt: new Date().toISOString(),
  },
];

export default function App() {
  const { route, navigate } = useHashRoute();
  const { isAuthenticated, login, logout, user } = useAuth();
  const [theme, setTheme] = useLocalStorage<ThemeMode>('sprint-sarthi-theme', 'dark');
  const [sidebarCollapsed, setSidebarCollapsed] = useLocalStorage('sprint-sarthi-sidebar-collapsed', false);
  const [selectedProject, setSelectedProject] = useLocalStorage('sprint-sarthi-project', 'Cloud Operations');
  const [draft, setDraft] = useLocalStorage<SprintDraft>('sprint-sarthi-draft-v3', initialDraft);
  const [files, setFiles] = useLocalStorage<QueuedFile[]>('sprint-sarthi-files-v3', initialFiles);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [commandOpen, setCommandOpen] = useState(false);
  const [newSprintOpen, setNewSprintOpen] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const { toasts, showToast, dismissToast } = useToast();

  // Apply theme (must be before any conditional returns to follow React hooks rules)
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.colorScheme = theme;
  }, [theme]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleShortcut = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setCommandOpen(true);
      }
    };

    window.addEventListener('keydown', handleShortcut);
    return () => window.removeEventListener('keydown', handleShortcut);
  }, []);

  // Show login page if not authenticated
  if (!isAuthenticated) {
    return <LoginPage onLogin={login} />;
  }

  const handleJiraSync = async () => {
    if (isSyncing) return;
    setIsSyncing(true);
    const result = await syncWithJira();
    setIsSyncing(false);
    showToast({
      tone: 'success',
      title: 'Jira sync complete',
      message: `${result.updatedIssues} issues updated across ${result.projects} projects.`,
    });
  };

  const handleSaveDraft = async () => {
    const result = await saveSprintDraft(draft);
    showToast({
      tone: 'success',
      title: 'Draft saved',
      message: `${result.id} was saved locally and is ready to continue.`,
    });
  };

  const handleCreateSprint = async () => {
    const result = await createSprint(draft);
    showToast({
      tone: 'success',
      title: 'Sprint plan created',
      message: `${result.name} is now available in Sprint Planning.`,
    });
    navigate('planning');
  };

  const handleQuickSprintCreate = (name: string, startDate: string, duration: string) => {
    setDraft((current) => ({ ...current, name, duration }));
    showToast({
      tone: 'success',
      title: 'New sprint draft created',
      message: `${name} starts on ${startDate}. Add scope when you are ready.`,
    });
    navigate('planning');
  };

  const handleModuleAction = (moduleRoute: Exclude<typeof route, 'dashboard'>) => {
    if (moduleRoute === 'planning') {
      setNewSprintOpen(true);
      return;
    }

    if (moduleRoute === 'jira') {
      void handleJiraSync();
      return;
    }

    showToast({
      tone: 'info',
      title: `${modulePages[moduleRoute].primaryAction} opened`,
      message: 'This demo action is ready to connect to your API or workflow.',
    });
  };

  const handleToggleSidebar = () => {
    // On mobile, toggle the overlay; on desktop, toggle collapsed
    if (window.innerWidth < 1024) {
      setMobileOpen((current) => !current);
    } else {
      setSidebarCollapsed((current) => !current);
    }
  };

  const topbar = (
    <Topbar
      route={route}
      selectedProject={selectedProject}
      isSyncing={isSyncing}
      theme={theme}
      onProjectChange={setSelectedProject}
      onToggleSidebar={handleToggleSidebar}
      onOpenCommand={() => setCommandOpen(true)}
      onSync={() => void handleJiraSync()}
      onNavigate={navigate}
      onToggleTheme={() => setTheme((current) => (current === 'dark' ? 'light' : 'dark'))}
      onLogout={logout}
    />
  );

  const sidebar = (
    <Sidebar
      route={route}
      collapsed={sidebarCollapsed}
      mobileOpen={mobileOpen}
      onNavigate={navigate}
      onCloseMobile={() => setMobileOpen(false)}
    />
  );

  return (
    <>
      <AppShell sidebar={sidebar} topbar={topbar} sidebarCollapsed={sidebarCollapsed}>
        {route === 'dashboard' ? (
          <DashboardPage
            project={selectedProject}
            draft={draft}
            setDraft={setDraft}
            files={files}
            setFiles={setFiles}
            onNavigate={navigate}
            onNewSprint={() => setNewSprintOpen(true)}
            onSaveDraft={handleSaveDraft}
            onCreateSprint={handleCreateSprint}
          />
        ) : (
          <ModulePage route={route} config={modulePages[route]} onPrimaryAction={handleModuleAction} />
        )}
      </AppShell>

      <CommandPalette open={commandOpen} onClose={() => setCommandOpen(false)} onNavigate={navigate} />
      <NewSprintModal
        open={newSprintOpen}
        onClose={() => setNewSprintOpen(false)}
        onCreate={handleQuickSprintCreate}
      />
      <ToastStack toasts={toasts} onDismiss={dismissToast} />
    </>
  );
}
