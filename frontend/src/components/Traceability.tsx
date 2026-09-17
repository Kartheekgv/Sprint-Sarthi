"use client";

import { useEffect, useState } from "react";
import { AlertCircle, BookOpen, FileText, Link2, Loader2, X } from "lucide-react";

export type BacklogItemType = "requirement" | "epic" | "story" | "task";

type SourceEvidence = {
  section_id: string;
  document_id: string;
  document_name: string;
  section: string;
  heading: string;
  page: number | null;
  chunk_index: number;
  snippet: string;
  reference: string;
};

type EvidenceResponse = {
  item_id: string;
  item_type: BacklogItemType;
  sources: SourceEvidence[];
  unresolved_references: string[];
};

type TraceabilityProps = {
  apiUrl: string;
  itemId: string;
  itemType: BacklogItemType;
  itemLabel: string;
  sourceCount: number;
};

export function Traceability({ apiUrl, itemId, itemType, itemLabel, sourceCount }: TraceabilityProps) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [evidence, setEvidence] = useState<EvidenceResponse | null>(null);

  useEffect(() => {
    if (!open) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [open]);

  async function viewSources() {
    setOpen(true);
    if (evidence || loading) return;
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`${apiUrl}/backlog/${itemType}/${itemId}/sources`);
      if (!response.ok) {
        const body = await response.json();
        throw new Error(body.detail ?? "Source evidence could not be loaded.");
      }
      setEvidence(await response.json());
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Source evidence could not be loaded.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <div className="flex flex-wrap items-center gap-2">
        <span className="inline-flex h-8 items-center gap-1.5 border border-[var(--success)] bg-white px-2.5 text-xs font-bold text-[var(--success)]" title="Linked to authoritative source evidence">
          <Link2 size={13} aria-hidden="true" /> Traceable · {sourceCount}
        </span>
        <button type="button" onClick={viewSources} disabled={sourceCount === 0} className="inline-flex h-8 items-center gap-1.5 px-2 text-xs font-bold text-[var(--accent)] underline-offset-4 hover:underline disabled:cursor-not-allowed disabled:opacity-45">
          <BookOpen size={14} aria-hidden="true" /> View Source
        </button>
      </div>

      {open && (
        <div className="fixed inset-0 z-50 bg-black/45" role="presentation" onMouseDown={(event) => { if (event.currentTarget === event.target) setOpen(false); }}>
          <aside role="dialog" aria-modal="true" aria-labelledby="source-panel-title" className="ml-auto flex h-full w-full max-w-xl flex-col overflow-hidden bg-white shadow-2xl">
            <header className="flex items-start justify-between gap-4 border-b border-[var(--line)] p-5">
              <div>
                <p className="text-xs font-bold uppercase text-[var(--accent)]">Traceability evidence</p>
                <h2 id="source-panel-title" className="mt-1 font-display text-xl font-semibold">{itemLabel}</h2>
                <p className="mt-1 text-sm text-[var(--muted)]">Authoritative excerpts retained from the uploaded source.</p>
              </div>
              <button type="button" onClick={() => setOpen(false)} className="grid size-9 shrink-0 place-items-center border border-[var(--line)]" aria-label="Close source evidence"><X size={18} /></button>
            </header>

            <div className="flex-1 overflow-y-auto p-5">
              {loading && <div className="flex items-center gap-2 text-sm text-[var(--muted)]"><Loader2 className="animate-spin" size={17} /> Loading evidence...</div>}
              {error && <div role="alert" className="flex gap-2 border-l-4 border-red-600 bg-red-50 p-3 text-sm text-red-800"><AlertCircle className="shrink-0" size={17} /> {error}</div>}
              {evidence && evidence.sources.length === 0 && <p className="text-sm text-[var(--muted)]">No source section could be resolved for this item.</p>}
              {evidence && evidence.sources.length > 0 && <ol className="grid gap-4">{evidence.sources.map((source) => (
                <li key={source.section_id} className="border border-[var(--line)] bg-[var(--soft)] p-4">
                  <div className="flex items-start justify-between gap-3">
                    <span className="flex items-center gap-2 text-sm font-bold"><FileText size={15} className="text-[var(--accent)]" /> {source.document_name}</span>
                    <span className="shrink-0 bg-white px-2 py-1 text-xs font-semibold">{source.page ? `Page ${source.page}` : "Page not available"}</span>
                  </div>
                  <dl className="mt-3 grid grid-cols-[72px_1fr] gap-x-3 gap-y-1 text-xs">
                    <dt className="text-[var(--muted)]">Section</dt><dd className="font-semibold">{source.section || "Document"}</dd>
                    <dt className="text-[var(--muted)]">Heading</dt><dd className="font-semibold">{source.heading || "Untitled section"}</dd>
                  </dl>
                  <blockquote className="mt-4 border-l-2 border-[var(--accent)] bg-white p-3 text-sm leading-6 text-[var(--ink)]">{source.snippet}</blockquote>
                </li>
              ))}</ol>}
              {evidence && evidence.unresolved_references.length > 0 && <div className="mt-4 border-l-4 border-amber-500 bg-amber-50 p-3 text-sm text-amber-900"><strong>Unresolved evidence:</strong> {evidence.unresolved_references.join("; ")}</div>}
            </div>
          </aside>
        </div>
      )}
    </>
  );
}
