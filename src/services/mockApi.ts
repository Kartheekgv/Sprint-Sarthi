import type { ChatMessage, SprintDraft } from '../types';

function wait(duration: number) {
  return new Promise((resolve) => window.setTimeout(resolve, duration));
}

export async function syncWithJira() {
  await wait(900);
  return {
    updatedIssues: 14,
    projects: 3,
    syncedAt: new Date().toISOString(),
  };
}

export async function saveSprintDraft(draft: SprintDraft) {
  await wait(600);
  return {
    id: `DRAFT-${Math.floor(1000 + Math.random() * 9000)}`,
    savedAt: new Date().toISOString(),
    draft,
  };
}

export async function createSprint(draft: SprintDraft) {
  await wait(1000);
  return {
    id: `SPR-${Math.floor(100 + Math.random() * 900)}`,
    name: draft.name,
    createdAt: new Date().toISOString(),
  };
}

const responseLibrary = [
  'Your sprint looks healthy overall. I would keep 12% of capacity uncommitted and resolve the backend dependency before adding another high-priority item.',
  'The strongest sprint goal is the one that describes user impact rather than a list of outputs. Try connecting the goal to reduced incident response time.',
  'I found one likely planning risk: backend allocation is above the preferred threshold. Moving a five-point item to the next sprint would create a safer plan.',
  'Three requirements are ready for planning. REQ-104 still needs a measurable outcome, while REQ-103 has enough context and acceptance criteria to estimate confidently.',
];

export async function askAssistant(prompt: string): Promise<ChatMessage> {
  await wait(850);
  const responseIndex = prompt.length % responseLibrary.length;
  return {
    id: crypto.randomUUID(),
    role: 'assistant',
    text: responseLibrary[responseIndex],
    timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
  };
}
