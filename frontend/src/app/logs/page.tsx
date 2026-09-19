"use client";

import { useEffect, useMemo, useState } from "react";
import { Activity, ArrowLeft, Bot, CheckCircle2, Clock3, RefreshCw, ScrollText, ShieldCheck, TriangleAlert } from "lucide-react";
import Link from "next/link";

type LogProject = { id: string; name: string };
type LogEntry = {
  id: string;
  kind: "audit" | "execution";
  created_at: string;
  project_id: string | null;
  project_name: string;
  session_id: string | null;
  source: string;
  status: string;
  message: string;
  metadata: Record<string, string | number | boolean | null>;
};
type LogsResponse = { entries: LogEntry[]; projects: LogProject[] };

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "/api/v1";

function formatValue(key: string, value: string | number | boolean | null) {
  if (value === null || value === "") return "Not reported";
  if (key === "duration_ms" && typeof value === "number") return `${(value / 1000).toFixed(2)} s`;
  return String(value);
}

export default function LogsPage() {
  const [data, setData] = useState<LogsResponse>({ entries: [], projects: [] });
  const [projectId, setProjectId] = useState("");
  const [kind, setKind] = useState("all");
  const [status, setStatus] = useState("all");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    const query = new URLSearchParams({ kind, limit: "500" });
    if (projectId) query.set("project_id", projectId);
    fetch(`${API_URL}/logs?${query}`, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error("Could not load operational logs.");
        return response.json();
      })
      .then((result: LogsResponse) => setData(result))
      .catch((cause) => {
        if (cause instanceof DOMException && cause.name === "AbortError") return;
        setError(cause instanceof Error ? cause.message : "Could not load operational logs.");
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [projectId, kind, refreshKey]);

  const statuses = useMemo(
    () => Array.from(new Set(data.entries.map((entry) => entry.status))).sort(),
    [data.entries],
  );
  const visibleEntries = useMemo(() => {
    const query = search.trim().toLowerCase();
    return data.entries.filter((entry) => {
      if (status !== "all" && entry.status !== status) return false;
      if (!query) return true;
      return [entry.message, entry.project_name, entry.source, entry.session_id, ...Object.values(entry.metadata)]
        .some((value) => String(value ?? "").toLowerCase().includes(query));
    });
  }, [data.entries, search, status]);
  const failures = data.entries.filter((entry) => entry.status === "failed").length;
  const executions = data.entries.filter((entry) => entry.kind === "execution");
  const averageDuration = executions.length
    ? Math.round(executions.reduce((sum, entry) => sum + Number(entry.metadata.duration_ms ?? 0), 0) / executions.length)
    : 0;

  function refresh() {
    setLoading(true);
    setError("");
    setRefreshKey((value) => value + 1);
  }

  return (
    <main className="min-h-screen bg-[var(--canvas)] text-[var(--ink)]">
      <header className="border-b border-[var(--line)] bg-white">
        <div className="mx-auto flex min-h-[72px] max-w-[1440px] flex-wrap items-center gap-4 px-5 py-3 lg:px-8">
          <Link href="/" className="flex items-center gap-3 font-bold">
            <span className="grid size-10 place-items-center bg-[var(--ink)] text-white"><Bot size={20} /></span>
            <span><strong className="block font-display text-lg">Sprint Sarthi</strong><small className="block text-[10px] uppercase text-[var(--muted)]">Operations</small></span>
          </Link>
          <div className="ml-auto flex items-center gap-2">
            <span className="hidden items-center gap-2 text-xs font-bold text-[var(--success)] sm:flex"><ShieldCheck size={15} /> Read-only view</span>
            <Link href="/" className="flex h-10 items-center gap-2 border border-[var(--line-strong)] bg-white px-3 text-xs font-bold"><ArrowLeft size={16} /> Back to workflow</Link>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-[1440px] px-5 py-8 lg:px-8">
        <div className="flex flex-wrap items-end justify-between gap-4 border-b border-[var(--line-strong)] pb-6">
          <div>
            <span className="text-xs font-bold uppercase text-[var(--accent)]">Operational evidence</span>
            <h1 className="mt-2 font-display text-3xl font-semibold">System logs</h1>
            <p className="mt-2 max-w-2xl text-sm text-[var(--muted)]">Persisted agent executions and governance events. Prompts, credentials, and provider payloads are not exposed.</p>
          </div>
          <button type="button" onClick={refresh} disabled={loading} className="flex h-10 items-center gap-2 bg-[var(--ink)] px-4 text-xs font-bold text-white disabled:opacity-50">
            <RefreshCw className={loading ? "animate-spin" : ""} size={15} /> Refresh
          </button>
        </div>

        <section className="grid gap-px border-y border-[var(--line)] bg-[var(--line)] sm:grid-cols-2 lg:grid-cols-4" aria-label="Log summary">
          {[
            ["Visible records", data.entries.length, <ScrollText key="records" size={18} />],
            ["Agent executions", executions.length, <Activity key="executions" size={18} />],
            ["Failed executions", failures, failures ? <TriangleAlert key="failures" size={18} /> : <CheckCircle2 key="healthy" size={18} />],
            ["Average duration", averageDuration ? `${(averageDuration / 1000).toFixed(1)} s` : "Not reported", <Clock3 key="duration" size={18} />],
          ].map(([label, value, icon]) => (
            <div key={String(label)} className="flex items-center justify-between bg-white p-4">
              <div><span className="text-[10px] font-bold uppercase text-[var(--muted)]">{label}</span><strong className="mt-1 block text-xl">{String(value)}</strong></div>
              <span className="text-[var(--accent)]">{icon}</span>
            </div>
          ))}
        </section>

        <section className="mt-6 grid gap-3 border border-[var(--line)] bg-white p-4 md:grid-cols-4" aria-label="Log filters">
          <label className="grid gap-1 text-xs font-bold">Project
            <select value={projectId} onChange={(event) => { setLoading(true); setError(""); setProjectId(event.target.value); }} className="h-10 border border-[var(--line-strong)] bg-white px-3 font-normal"><option value="">All projects</option>{data.projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}</select>
          </label>
          <label className="grid gap-1 text-xs font-bold">Record type
            <select value={kind} onChange={(event) => { setLoading(true); setError(""); setKind(event.target.value); }} className="h-10 border border-[var(--line-strong)] bg-white px-3 font-normal"><option value="all">All records</option><option value="execution">Agent executions</option><option value="audit">Audit events</option></select>
          </label>
          <label className="grid gap-1 text-xs font-bold">Status
            <select value={status} onChange={(event) => setStatus(event.target.value)} className="h-10 border border-[var(--line-strong)] bg-white px-3 font-normal"><option value="all">All statuses</option>{statuses.map((item) => <option key={item} value={item}>{item}</option>)}</select>
          </label>
          <label className="grid gap-1 text-xs font-bold">Search
            <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Agent, action, session..." className="h-10 border border-[var(--line-strong)] bg-white px-3 font-normal" />
          </label>
        </section>

        {error && <p className="mt-5 border-l-4 border-red-600 bg-red-50 p-4 text-sm text-red-900" role="alert">{error}</p>}
        <section className="mt-6 border border-[var(--line)] bg-white" aria-label="Log timeline">
          <div className="flex items-center justify-between border-b border-[var(--line)] bg-[var(--soft)] px-4 py-3 text-xs font-bold"><span>Newest first</span><span className="text-[var(--muted)]">{visibleEntries.length} shown</span></div>
          {loading && data.entries.length === 0 ? (
            <div className="p-10 text-center text-sm text-[var(--muted)]">Loading operational history...</div>
          ) : visibleEntries.length === 0 ? (
            <div className="p-10 text-center text-sm text-[var(--muted)]">No records match these filters.</div>
          ) : (
            <div className="divide-y divide-[var(--line)]">
              {visibleEntries.map((entry) => (
                <article key={`${entry.kind}-${entry.id}`} className="grid gap-3 p-4 lg:grid-cols-[180px_150px_minmax(0,1fr)]">
                  <time className="text-xs text-[var(--muted)]" dateTime={entry.created_at}>{new Date(entry.created_at).toLocaleString()}</time>
                  <div><span className={`inline-flex px-2 py-1 text-[10px] font-bold uppercase ${entry.kind === "execution" ? "bg-orange-100 text-orange-900" : "bg-green-100 text-green-900"}`}>{entry.kind}</span><span className="ml-2 text-xs font-bold capitalize">{entry.status}</span></div>
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-start justify-between gap-2"><strong className="text-sm">{entry.message.replaceAll("_", " ")}</strong><span className="text-xs text-[var(--muted)]">{entry.project_name}</span></div>
                    <p className="mt-1 text-xs text-[var(--muted)]">Source: {entry.source}{entry.session_id ? ` · Session ${entry.session_id}` : ""}</p>
                    <details className="mt-3 text-xs"><summary className="cursor-pointer font-bold text-[var(--accent)]">View metadata</summary><dl className="mt-2 grid gap-x-4 gap-y-2 border-l-2 border-[var(--line)] pl-3 sm:grid-cols-2">{Object.entries(entry.metadata).map(([key, value]) => <div key={key} className="min-w-0"><dt className="font-bold capitalize text-[var(--muted)]">{key.replaceAll("_", " ")}</dt><dd className="mt-0.5 break-all">{formatValue(key, value)}</dd></div>)}</dl></details>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
