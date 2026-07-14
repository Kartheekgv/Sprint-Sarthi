import type { Dispatch, SetStateAction } from 'react';
import type { QueuedFile, RouteId, SprintDraft } from '../../types';
import { ActivityFeed } from '../dashboard/ActivityFeed';
import { AICopilot } from '../dashboard/AICopilot';
import { RecentWork } from '../dashboard/RecentWork';
import { RequirementsWorkspace } from '../dashboard/RequirementsWorkspace';
import { SprintPulse } from '../dashboard/SprintPulse';
import { StatsGrid } from '../dashboard/StatsGrid';
import { WelcomeHero } from '../dashboard/WelcomeHero';

interface DashboardPageProps {
  project: string;
  draft: SprintDraft;
  setDraft: Dispatch<SetStateAction<SprintDraft>>;
  files: QueuedFile[];
  setFiles: Dispatch<SetStateAction<QueuedFile[]>>;
  onNavigate: (route: RouteId) => void;
  onNewSprint: () => void;
  onSaveDraft: () => Promise<void>;
  onCreateSprint: () => Promise<void>;
}

export function DashboardPage({
  project,
  draft,
  setDraft,
  files,
  setFiles,
  onNavigate,
  onNewSprint,
  onSaveDraft,
  onCreateSprint,
}: DashboardPageProps) {
  return (
    <div className="dashboard-page page-enter">
      <WelcomeHero project={project} onOpenPlanning={() => onNavigate('planning')} onNewSprint={onNewSprint} />
      <StatsGrid />

      <div className="dashboard-primary-grid">
        <RequirementsWorkspace
          draft={draft}
          setDraft={setDraft}
          files={files}
          setFiles={setFiles}
          onSaveDraft={onSaveDraft}
          onCreateSprint={onCreateSprint}
        />
        <aside className="dashboard-right-rail">
          <AICopilot />
          <SprintPulse />
        </aside>
      </div>

      <div className="dashboard-secondary-grid">
        <RecentWork />
        <ActivityFeed onNavigate={onNavigate} />
      </div>
    </div>
  );
}
