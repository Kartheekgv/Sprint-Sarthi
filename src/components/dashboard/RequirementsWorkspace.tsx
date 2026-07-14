import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  Check,
  CheckCircle2,
  FileText,
  FolderOpen,
  Paperclip,
  Save,
  Trash2,
  UploadCloud,
  UsersRound,
} from 'lucide-react';
import {
  useMemo,
  useRef,
  useState,
  type ChangeEvent,
  type Dispatch,
  type DragEvent,
  type SetStateAction,
} from 'react';
import type { QueuedFile, SprintDraft } from '../../types';
import { formatFileSize } from '../../utils/formatters';
import { Button } from '../common/Button';
import { Panel } from '../common/Panel';

interface RequirementsWorkspaceProps {
  draft: SprintDraft;
  setDraft: Dispatch<SetStateAction<SprintDraft>>;
  files: QueuedFile[];
  setFiles: Dispatch<SetStateAction<QueuedFile[]>>;
  onSaveDraft: () => Promise<void>;
  onCreateSprint: () => Promise<void>;
}

type DraftErrors = Partial<Record<keyof SprintDraft, string>>;

const steps = [
  { title: 'Project context', description: 'Goal, owner and capacity' },
  { title: 'Supporting files', description: 'Briefs, notes and evidence' },
  { title: 'Review and confirm', description: 'Validate planning readiness' },
];

const maxFileSize = 100 * 1024 * 1024;

export function RequirementsWorkspace({
  draft,
  setDraft,
  files,
  setFiles,
  onSaveDraft,
  onCreateSprint,
}: RequirementsWorkspaceProps) {
  const [step, setStep] = useState(0);
  const [errors, setErrors] = useState<DraftErrors>({});
  const [dragging, setDragging] = useState(false);
  const [saving, setSaving] = useState(false);
  const [creating, setCreating] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const updateDraft = <K extends keyof SprintDraft>(key: K, value: SprintDraft[K]) => {
    setDraft((current) => ({ ...current, [key]: value }));
    setErrors((current) => ({ ...current, [key]: undefined }));
  };

  const readiness = useMemo(() => {
    const checks = [
      Boolean(draft.name.trim()),
      draft.objective.trim().length >= 25,
      Boolean(draft.owner.trim()),
      Boolean(draft.team.trim()),
      Number(draft.capacity) > 0,
      Boolean(draft.definitionOfDone.trim()),
      files.length > 0,
    ];
    return Math.round((checks.filter(Boolean).length / checks.length) * 100);
  }, [draft, files.length]);

  const validateProjectContext = () => {
    const nextErrors: DraftErrors = {};
    if (!draft.name.trim()) nextErrors.name = 'Enter a sprint or initiative name.';
    if (draft.objective.trim().length < 25) nextErrors.objective = 'Describe the outcome in at least 25 characters.';
    if (!draft.owner.trim()) nextErrors.owner = 'Add the accountable owner.';
    if (!draft.team.trim()) nextErrors.team = 'Select or enter a team.';
    if (!draft.capacity || Number(draft.capacity) <= 0) nextErrors.capacity = 'Enter the available team hours.';
    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const nextStep = () => {
    if (step === 0 && !validateProjectContext()) return;
    setStep((current) => Math.min(current + 1, steps.length - 1));
  };

  const addFiles = (selectedFiles: File[]) => {
    const acceptedFiles = selectedFiles
      .filter((file) => file.size <= maxFileSize)
      .filter((file) => !files.some((queuedFile) => queuedFile.name === file.name && queuedFile.size === file.size))
      .map<QueuedFile>((file) => ({
        id: crypto.randomUUID(),
        name: file.name,
        size: file.size,
        type: file.type || 'application/octet-stream',
        addedAt: new Date().toISOString(),
      }));

    if (acceptedFiles.length) {
      setFiles((current) => [...current, ...acceptedFiles]);
    }
  };

  const handleFileInput = (event: ChangeEvent<HTMLInputElement>) => {
    addFiles(Array.from(event.target.files ?? []));
    event.target.value = '';
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragging(false);
    addFiles(Array.from(event.dataTransfer.files));
  };

  const saveDraft = async () => {
    setSaving(true);
    await onSaveDraft();
    setSaving(false);
  };

  const createSprint = async () => {
    if (!validateProjectContext()) {
      setStep(0);
      return;
    }
    setCreating(true);
    await onCreateSprint();
    setCreating(false);
  };

  return (
    <Panel
      className="requirements-workspace"
      eyebrow="Planning workspace"
      title="Turn requirements into a sprint-ready plan"
      description="Capture the minimum useful context first. Sprint Sarthi keeps the form focused and shows what is still missing."
      action={
        <div className="readiness-label">
          <span>Readiness</span>
          <strong>{readiness}%</strong>
        </div>
      }
    >
      <div className="workflow-steps" aria-label="Requirement intake progress">
        {steps.map((item, index) => (
          <button
            key={item.title}
            className={`workflow-step ${index === step ? 'is-current' : ''} ${index < step ? 'is-complete' : ''}`}
            onClick={() => {
              if (index === 0 || index <= step || validateProjectContext()) setStep(index);
            }}
          >
            <span className="workflow-step__number">{index < step ? <Check size={16} /> : index + 1}</span>
            <span>
              <strong>{item.title}</strong>
              <small>{item.description}</small>
            </span>
          </button>
        ))}
      </div>

      <div className="requirements-layout">
        <div className="requirements-layout__main">
          {step === 0 ? (
            <div className="form-section">
              <div className="form-grid form-grid--two">
                <label className={`field ${errors.name ? 'has-error' : ''}`}>
                  <span className="field__label">
                    Project or sprint name <em>*</em>
                  </span>
                  <input
                    value={draft.name}
                    onChange={(event) => updateDraft('name', event.target.value)}
                    placeholder="e.g. Cloud Operations Sprint 25"
                  />
                  {errors.name ? <small className="field__error">{errors.name}</small> : null}
                </label>
                <label className="field">
                  <span className="field__label">Product area</span>
                  <select value={draft.productArea} onChange={(event) => updateDraft('productArea', event.target.value)}>
                    <option>Cloud Operations</option>
                    <option>Fleet Experience</option>
                    <option>Customer Portal</option>
                    <option>Platform Engineering</option>
                  </select>
                </label>
              </div>

              <label className={`field ${errors.objective ? 'has-error' : ''}`}>
                <span className="field__label">
                  Sprint goal and expected outcome <em>*</em>
                </span>
                <textarea
                  value={draft.objective}
                  onChange={(event) => updateDraft('objective', event.target.value)}
                  placeholder="Describe the user or business outcome this sprint should achieve."
                  rows={4}
                />
                <span className="field__meta">
                  {errors.objective ? <small className="field__error">{errors.objective}</small> : <small>Focus on outcome, not a list of tasks.</small>}
                  <small>{draft.objective.length} characters</small>
                </span>
              </label>

              <div className="form-grid form-grid--three">
                <label className={`field ${errors.owner ? 'has-error' : ''}`}>
                  <span className="field__label">Accountable owner *</span>
                  <input
                    value={draft.owner}
                    onChange={(event) => updateDraft('owner', event.target.value)}
                    placeholder="Name or email"
                  />
                  {errors.owner ? <small className="field__error">{errors.owner}</small> : null}
                </label>
                <label className={`field ${errors.team ? 'has-error' : ''}`}>
                  <span className="field__label">Delivery team *</span>
                  <input
                    value={draft.team}
                    onChange={(event) => updateDraft('team', event.target.value)}
                    placeholder="e.g. Cloud Platform"
                  />
                  {errors.team ? <small className="field__error">{errors.team}</small> : null}
                </label>
                <label className={`field ${errors.capacity ? 'has-error' : ''}`}>
                  <span className="field__label">Available capacity *</span>
                  <div className="input-suffix">
                    <input
                      type="number"
                      min="1"
                      value={draft.capacity}
                      onChange={(event) => updateDraft('capacity', event.target.value)}
                      placeholder="240"
                    />
                    <span>hours</span>
                  </div>
                  {errors.capacity ? <small className="field__error">{errors.capacity}</small> : null}
                </label>
              </div>

              <div className="form-grid form-grid--two">
                <label className="field">
                  <span className="field__label">Sprint duration</span>
                  <select value={draft.duration} onChange={(event) => updateDraft('duration', event.target.value)}>
                    <option value="5">5 working days</option>
                    <option value="10">10 working days</option>
                    <option value="15">15 working days</option>
                  </select>
                </label>
                <label className="field">
                  <span className="field__label">Planning priority</span>
                  <select
                    value={draft.priority}
                    onChange={(event) => updateDraft('priority', event.target.value as SprintDraft['priority'])}
                  >
                    <option>Low</option>
                    <option>Medium</option>
                    <option>High</option>
                    <option>Critical</option>
                  </select>
                </label>
              </div>

              <label className="field">
                <span className="field__label">Definition of done</span>
                <textarea
                  value={draft.definitionOfDone}
                  onChange={(event) => updateDraft('definitionOfDone', event.target.value)}
                  placeholder="What must be true for the sprint goal to be considered complete?"
                  rows={3}
                />
              </label>
            </div>
          ) : null}

          {step === 1 ? (
            <div className="upload-step">
              <div
                className={`drop-zone ${dragging ? 'is-dragging' : ''}`}
                onDragEnter={(event) => {
                  event.preventDefault();
                  setDragging(true);
                }}
                onDragOver={(event) => event.preventDefault()}
                onDragLeave={() => setDragging(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                role="button"
                tabIndex={0}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' || event.key === ' ') fileInputRef.current?.click();
                }}
              >
                <input ref={fileInputRef} type="file" multiple onChange={handleFileInput} hidden />
                <span className="drop-zone__icon">
                  <UploadCloud size={28} />
                </span>
                <h3>Drop files here or browse</h3>
                <p>Upload briefs, research notes, recordings, diagrams, or spreadsheets.</p>
                <small>Maximum 100 MB per file. Duplicate files are ignored.</small>
              </div>

              <div className="file-queue">
                <div className="file-queue__header">
                  <div>
                    <h3>Supporting files</h3>
                    <p>{files.length ? `${files.length} file${files.length > 1 ? 's' : ''} ready to use` : 'No files added yet'}</p>
                  </div>
                  <Button size="sm" icon={<Paperclip size={15} />} onClick={() => fileInputRef.current?.click()}>
                    Add files
                  </Button>
                </div>

                {files.length ? (
                  <div className="file-list">
                    {files.map((file) => (
                      <div className="file-row" key={file.id}>
                        <span className="file-row__icon">
                          <FileText size={18} />
                        </span>
                        <span className="file-row__copy">
                          <strong>{file.name}</strong>
                          <small>{formatFileSize(file.size)} · Ready for analysis</small>
                        </span>
                        <span className="file-row__status">
                          <CheckCircle2 size={15} /> Ready
                        </span>
                        <button
                          className="icon-button icon-button--danger"
                          onClick={() => setFiles((current) => current.filter((item) => item.id !== file.id))}
                          aria-label={`Remove ${file.name}`}
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="empty-files">
                    <FolderOpen size={28} />
                    <p>Files are optional, but they help the assistant generate more specific recommendations.</p>
                  </div>
                )}
              </div>
            </div>
          ) : null}

          {step === 2 ? (
            <div className="review-step">
              <div className="review-callout">
                <span className="review-callout__icon">
                  {readiness >= 80 ? <CheckCircle2 size={22} /> : <AlertCircle size={22} />}
                </span>
                <div>
                  <h3>{readiness >= 80 ? 'This plan is ready for final review' : 'A little more context will improve the plan'}</h3>
                  <p>
                    Readiness is {readiness}%. You can still create the sprint now, or return to complete the remaining context.
                  </p>
                </div>
              </div>

              <div className="review-grid">
                <article>
                  <small>Sprint name</small>
                  <strong>{draft.name || 'Not provided'}</strong>
                </article>
                <article>
                  <small>Owner</small>
                  <strong>{draft.owner || 'Not provided'}</strong>
                </article>
                <article>
                  <small>Team</small>
                  <strong>{draft.team || 'Not provided'}</strong>
                </article>
                <article>
                  <small>Capacity</small>
                  <strong>{draft.capacity ? `${draft.capacity} hours` : 'Not provided'}</strong>
                </article>
                <article>
                  <small>Duration</small>
                  <strong>{draft.duration} working days</strong>
                </article>
                <article>
                  <small>Priority</small>
                  <strong>{draft.priority}</strong>
                </article>
              </div>

              <article className="review-text">
                <small>Expected outcome</small>
                <p>{draft.objective || 'No outcome has been provided.'}</p>
              </article>

              <div className="review-checklist">
                <h3>Planning checklist</h3>
                {[
                  ['Clear sprint goal', Boolean(draft.objective.trim().length >= 25)],
                  ['Named owner and team', Boolean(draft.owner.trim() && draft.team.trim())],
                  ['Capacity recorded', Number(draft.capacity) > 0],
                  ['Definition of done', Boolean(draft.definitionOfDone.trim())],
                  ['Supporting evidence', files.length > 0],
                ].map(([label, complete]) => (
                  <div key={String(label)} className={complete ? 'is-complete' : ''}>
                    <span>{complete ? <Check size={15} /> : <AlertCircle size={15} />}</span>
                    {label}
                  </div>
                ))}
              </div>
            </div>
          ) : null}

          <div className="workflow-actions">
            <div>
              <Button icon={<Save size={16} />} onClick={saveDraft} disabled={saving}>
                {saving ? 'Saving...' : 'Save draft'}
              </Button>
            </div>
            <div className="workflow-actions__right">
              {step > 0 ? (
                <Button icon={<ArrowLeft size={16} />} onClick={() => setStep((current) => current - 1)}>
                  Back
                </Button>
              ) : null}
              {step < 2 ? (
                <Button variant="primary" trailingIcon={<ArrowRight size={16} />} onClick={nextStep}>
                  {step === 0 ? 'Continue to files' : 'Review plan'}
                </Button>
              ) : (
                <Button variant="primary" trailingIcon={<ArrowRight size={16} />} onClick={createSprint} disabled={creating}>
                  {creating ? 'Creating...' : 'Create sprint plan'}
                </Button>
              )}
            </div>
          </div>
        </div>

        <aside className="planning-preview">
          <div className="planning-preview__header">
            <span className="planning-preview__icon">
              <UsersRound size={20} />
            </span>
            <div>
              <small>Live planning preview</small>
              <strong>{draft.team || 'Your delivery team'}</strong>
            </div>
          </div>

          <div className="readiness-meter">
            <div className="readiness-meter__value">
              <strong>{readiness}%</strong>
              <span>ready</span>
            </div>
            <div className="readiness-meter__track">
              <span style={{ width: `${readiness}%` }} />
            </div>
          </div>

          <div className="preview-metrics">
            <div>
              <small>Duration</small>
              <strong>{draft.duration} days</strong>
            </div>
            <div>
              <small>Capacity</small>
              <strong>{draft.capacity || '0'}h</strong>
            </div>
            <div>
              <small>Priority</small>
              <strong>{draft.priority}</strong>
            </div>
            <div>
              <small>Files</small>
              <strong>{files.length}</strong>
            </div>
          </div>

          <div className="preview-guidance">
            <h3>What improves readiness?</h3>
            <ul>
              <li className={draft.objective.trim().length >= 25 ? 'is-complete' : ''}>
                <span>{draft.objective.trim().length >= 25 ? <Check size={14} /> : '1'}</span>
                Write a measurable sprint outcome.
              </li>
              <li className={Boolean(draft.definitionOfDone.trim()) ? 'is-complete' : ''}>
                <span>{draft.definitionOfDone.trim() ? <Check size={14} /> : '2'}</span>
                Define how the team knows it is done.
              </li>
              <li className={files.length > 0 ? 'is-complete' : ''}>
                <span>{files.length > 0 ? <Check size={14} /> : '3'}</span>
                Add evidence or supporting context.
              </li>
            </ul>
          </div>
        </aside>
      </div>
    </Panel>
  );
}
