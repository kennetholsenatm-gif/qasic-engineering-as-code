import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  LayoutGrid,
  FolderOpen,
  Play,
  FileBarChart,
  Loader2,
  ArrowRight,
  Box,
  ExternalLink,
} from 'lucide-react'
import RunPipeline from './RunPipeline'
import ResizableSplit from '../components/ResizableSplit'
import WorkspaceViewerPane from '../components/WorkspaceViewerPane'
import TerminalPanel from '../components/TerminalPanel'
import { WorkspaceCanvasProvider } from '../contexts/WorkspaceCanvasContext'

function fetchProject(apiBase, projectId) {
  return fetch(`${apiBase}/api/projects/${projectId}`).then(async (r) => {
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText)
    return r.json()
  })
}

function fetchProjectRuns(apiBase, projectId) {
  return fetch(`${apiBase}/api/projects/${projectId}/runs`).then(async (r) => {
    if (!r.ok) return { runs: [] }
    return r.json()
  })
}

function formatDate(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' })
  } catch {
    return '—'
  }
}

const TABS = [
  { id: 'overview', label: 'Overview', icon: LayoutGrid },
  { id: 'canvas', label: 'Canvas', icon: Play },
  { id: 'executions', label: 'Executions', icon: FileBarChart },
  { id: 'artifacts', label: 'Artifacts', icon: Box },
]

function fetchRunArtifacts(apiBase, projectId, runId) {
  return fetch(`${apiBase}/api/projects/${projectId}/runs/${runId}/artifacts`).then(async (r) => {
    if (!r.ok) return { artifacts: [] }
    return r.json()
  })
}

function fetchCompareRuns(apiBase, runIdA, runIdB) {
  return fetch(`${apiBase}/api/runs/compare?run_id_a=${runIdA}&run_id_b=${runIdB}`).then(async (r) => {
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText)
    return r.json()
  })
}

function ArtifactsTab({ apiBase, projectId, runs }) {
  const [selectedRunId, setSelectedRunId] = useState(runs[0]?.id ?? null)
  const { data: artifactsData, isLoading } = useQuery({
    queryKey: ['run-artifacts', apiBase, projectId, selectedRunId],
    queryFn: () => fetchRunArtifacts(apiBase, projectId, selectedRunId),
    enabled: !!projectId && !!selectedRunId,
  })
  const artifacts = artifactsData?.artifacts ?? []
  const baseUrl = apiBase.replace(/\/$/, '')

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-medium text-slate-100">Run artifacts</h2>
      <label className="flex items-center gap-2">
        <span className="text-sm text-slate-400">Run</span>
        <select
          value={selectedRunId ?? ''}
          onChange={(e) => setSelectedRunId(e.target.value ? Number(e.target.value) : null)}
          className="rounded border border-slate-600 bg-slate-800 px-3 py-1.5 text-sm text-slate-200"
        >
          <option value="">Select a run</option>
          {runs.map((r) => (
            <option key={r.id} value={r.id}>
              Run #{r.id} — {r.status} — {formatDate(r.started_at)}
            </option>
          ))}
        </select>
      </label>
      {!selectedRunId && (
        <p className="text-sm text-slate-500">Select a run to list its artifacts.</p>
      )}
      {selectedRunId && isLoading && (
        <div className="flex items-center gap-2 text-slate-500">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span className="text-sm">Loading artifacts…</span>
        </div>
      )}
      {selectedRunId && !isLoading && artifacts.length === 0 && (
        <p className="text-sm text-slate-500">No artifacts for this run.</p>
      )}
      {selectedRunId && !isLoading && artifacts.length > 0 && (
        <ul className="rounded-xl border border-slate-700/60 divide-y divide-slate-700/60">
          {artifacts.map((a) => (
            <li key={a.name} className="flex items-center justify-between px-4 py-3 hover:bg-slate-800/40">
              <span className="text-sm text-slate-200">{a.name}</span>
              <a
                href={a.url.startsWith('http') ? a.url : `${baseUrl}${a.url}`}
                download
                className="text-sm text-sky-400 hover:underline"
              >
                Download
              </a>
            </li>
          ))}
        </ul>
      )}
      <CompareRunsSection apiBase={apiBase} runs={runs} />
    </div>
  )
}

function CompareRunsSection({ apiBase, runs }) {
  const [runIdA, setRunIdA] = useState(runs[0]?.id ?? null)
  const [runIdB, setRunIdB] = useState(runs[1]?.id ?? null)
  const { data: compareData, isLoading, error } = useQuery({
    queryKey: ['compare-runs', apiBase, runIdA, runIdB],
    queryFn: () => fetchCompareRuns(apiBase, runIdA, runIdB),
    enabled: !!runIdA && !!runIdB && runIdA !== runIdB,
  })

  return (
    <div className="mt-8 pt-6 border-t border-slate-700/60">
      <h3 className="text-md font-medium text-slate-200 mb-3">Compare runs</h3>
      <div className="flex flex-wrap items-center gap-4 mb-4">
        <label className="flex items-center gap-2">
          <span className="text-sm text-slate-400">Run A</span>
          <select
            value={runIdA ?? ''}
            onChange={(e) => setRunIdA(e.target.value ? Number(e.target.value) : null)}
            className="rounded border border-slate-600 bg-slate-800 px-2 py-1.5 text-sm text-slate-200"
          >
            <option value="">—</option>
            {runs.map((r) => (
              <option key={r.id} value={r.id}>#{r.id} {r.status}</option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-2">
          <span className="text-sm text-slate-400">Run B</span>
          <select
            value={runIdB ?? ''}
            onChange={(e) => setRunIdB(e.target.value ? Number(e.target.value) : null)}
            className="rounded border border-slate-600 bg-slate-800 px-2 py-1.5 text-sm text-slate-200"
          >
            <option value="">—</option>
            {runs.map((r) => (
              <option key={r.id} value={r.id}>#{r.id} {r.status}</option>
            ))}
          </select>
        </label>
      </div>
      {runIdA && runIdB && runIdA === runIdB && (
        <p className="text-sm text-slate-500">Select two different runs.</p>
      )}
      {runIdA && runIdB && runIdA !== runIdB && isLoading && (
        <div className="flex items-center gap-2 text-slate-500">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span className="text-sm">Loading comparison…</span>
        </div>
      )}
      {runIdA && runIdB && runIdA !== runIdB && error && (
        <p className="text-sm text-red-400">{error.message}</p>
      )}
      {runIdA && runIdB && runIdA !== runIdB && compareData && (
        <div className="grid grid-cols-2 gap-4">
          <div className="rounded-xl border border-slate-700/60 bg-slate-800/60 p-4">
            <h4 className="text-sm font-semibold text-slate-300 mb-2">Run #{compareData.run_a.id}</h4>
            <dl className="space-y-1 text-sm">
              <div><span className="text-slate-500">Status:</span> <span className="text-slate-200">{compareData.run_a.status}</span></div>
              <div><span className="text-slate-500">Started:</span> <span className="text-slate-200">{formatDate(compareData.run_a.started_at)}</span></div>
              {compareData.run_a.routing_cost != null && <div><span className="text-slate-500">Routing cost:</span> <span className="text-slate-200">{String(compareData.run_a.routing_cost)}</span></div>}
              {compareData.run_a.phase_mean != null && <div><span className="text-slate-500">Phase mean:</span> <span className="text-slate-200">{String(compareData.run_a.phase_mean)}</span></div>}
            </dl>
          </div>
          <div className="rounded-xl border border-slate-700/60 bg-slate-800/60 p-4">
            <h4 className="text-sm font-semibold text-slate-300 mb-2">Run #{compareData.run_b.id}</h4>
            <dl className="space-y-1 text-sm">
              <div><span className="text-slate-500">Status:</span> <span className="text-slate-200">{compareData.run_b.status}</span></div>
              <div><span className="text-slate-500">Started:</span> <span className="text-slate-200">{formatDate(compareData.run_b.started_at)}</span></div>
              {compareData.run_b.routing_cost != null && <div><span className="text-slate-500">Routing cost:</span> <span className="text-slate-200">{String(compareData.run_b.routing_cost)}</span></div>}
              {compareData.run_b.phase_mean != null && <div><span className="text-slate-500">Phase mean:</span> <span className="text-slate-200">{String(compareData.run_b.phase_mean)}</span></div>}
            </dl>
          </div>
        </div>
      )}
    </div>
  )
}

export default function ProjectWorkspace({ apiBase }) {
  const { projectId: projectIdParam } = useParams()
  const projectId = projectIdParam ? Number(projectIdParam) : null
  const [activeTab, setActiveTab] = useState('overview')

  const { data: project, isLoading: projectLoading, error: projectError } = useQuery({
    queryKey: ['project', apiBase, projectId],
    queryFn: () => fetchProject(apiBase, projectId),
    enabled: !!projectId,
  })

  const { data: runsData, isLoading: runsLoading } = useQuery({
    queryKey: ['project-runs', apiBase, projectId],
    queryFn: () => fetchProjectRuns(apiBase, projectId),
    enabled: !!projectId,
    staleTime: 10_000,
  })
  const runs = runsData?.runs || []
  const lastRun = runs[0] || null

  if (!projectId) {
    return (
      <div className="rounded-xl border border-amber-500/40 bg-amber-950/20 px-4 py-3 text-amber-200">
        Invalid project. <Link to="/projects" className="text-sky-400 hover:underline">Back to Projects</Link>
      </div>
    )
  }

  if (projectError) {
    return (
      <div className="rounded-xl border border-red-500/40 bg-red-950/20 px-4 py-3 text-red-200">
        {projectError.message}. <Link to="/projects" className="text-sky-400 hover:underline">Back to Projects</Link>
      </div>
    )
  }

  if (projectLoading || !project) {
    return (
      <div className="flex items-center gap-2 text-slate-500">
        <Loader2 className="h-5 w-5 animate-spin" />
        <span>Loading project…</span>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Workspace tabs */}
      <div className="flex flex-wrap items-center gap-2 border-b border-slate-700/60 pb-3">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => setActiveTab(id)}
            className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
              activeTab === id
                ? 'bg-sky-500/20 text-sky-300'
                : 'text-slate-400 hover:bg-slate-700/60 hover:text-slate-200'
            }`}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </div>

      {activeTab === 'overview' && (
        <div className="space-y-6">
          <div>
            <h1 className="text-2xl font-semibold text-slate-100">{project.name}</h1>
            {project.description && (
              <p className="mt-1 text-slate-400">{project.description}</p>
            )}
          </div>
          {lastRun && (
            <div className="rounded-xl border border-slate-700/60 bg-slate-800/60 p-4">
              <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-500">Last run</h2>
              <p className="mt-1 text-slate-200">
                Run #{lastRun.id} — {lastRun.status} — {formatDate(lastRun.started_at)}
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Link
                  to={`/results?project_id=${projectId}`}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-sky-500/50 bg-sky-500/10 px-3 py-1.5 text-sm text-sky-400 transition-colors hover:bg-sky-500/20"
                >
                  <FileBarChart className="h-4 w-4" />
                  View last results
                </Link>
                <button
                  type="button"
                  onClick={() => setActiveTab('canvas')}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-sky-500/50 bg-sky-500/10 px-3 py-1.5 text-sm text-sky-400 transition-colors hover:bg-sky-500/20"
                >
                  <Play className="h-4 w-4" />
                  Open in Canvas
                </button>
              </div>
            </div>
          )}
          {!lastRun && (
            <div className="rounded-xl border border-slate-700/60 bg-slate-800/60 p-4 text-slate-400">
              No runs yet. Open the Canvas tab to run the pipeline.
            </div>
          )}
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setActiveTab('canvas')}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-600 bg-slate-700/60 px-4 py-2 text-sm text-slate-200 hover:bg-slate-700"
            >
              Open in Canvas <ArrowRight className="h-4 w-4" />
            </button>
            <Link
              to={`/results?project_id=${projectId}`}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-600 bg-slate-700/60 px-4 py-2 text-sm text-slate-200 hover:bg-slate-700"
            >
              View last results <ExternalLink className="h-4 w-4" />
            </Link>
          </div>
        </div>
      )}

      {activeTab === 'canvas' && (
        <div className="min-h-[500px] flex flex-col" style={{ height: 'calc(100vh - 12rem)' }}>
          <WorkspaceCanvasProvider>
            <div className="flex flex-1 min-h-0 flex-col">
              <ResizableSplit
                defaultRatio={0.55}
                minLeft={320}
                minRight={280}
                left={
                  <div className="h-full overflow-auto rounded-l-xl border border-slate-700/60 bg-slate-900/50">
                    <RunPipeline apiBase={apiBase} initialProjectId={projectId} />
                  </div>
                }
                right={
                  <WorkspaceViewerPane apiBase={apiBase} projectId={projectId} />
                }
              />
              <TerminalPanel apiBase={apiBase} />
            </div>
          </WorkspaceCanvasProvider>
        </div>
      )}

      {activeTab === 'executions' && (
        <div className="space-y-3">
          <h2 className="text-lg font-medium text-slate-100">Pipeline runs</h2>
          {runsLoading ? (
            <div className="flex items-center gap-2 text-slate-500">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span className="text-sm">Loading runs…</span>
            </div>
          ) : runs.length === 0 ? (
            <p className="text-sm text-slate-500">No runs yet. Use the Canvas tab to run the pipeline.</p>
          ) : (
            <div className="overflow-x-auto rounded-xl border border-slate-700/60">
              <table className="w-full border-collapse text-sm">
                <thead>
                  <tr className="border-b border-slate-700 bg-slate-800/80">
                    <th className="px-4 py-3 text-left font-medium text-slate-400">Run ID</th>
                    <th className="px-4 py-3 text-left font-medium text-slate-400">Status</th>
                    <th className="px-4 py-3 text-left font-medium text-slate-400">Started</th>
                    <th className="px-4 py-3 text-left font-medium text-slate-400">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.map((run) => (
                    <tr key={run.id} className="border-b border-slate-700/60 hover:bg-slate-800/40">
                      <td className="px-4 py-3 font-mono text-slate-200">{run.id}</td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                            run.status === 'success'
                              ? 'bg-emerald-500/20 text-emerald-300'
                              : run.status === 'failed'
                                ? 'bg-red-500/20 text-red-300'
                                : run.status === 'running'
                                  ? 'bg-sky-500/20 text-sky-300'
                                  : 'bg-slate-500/20 text-slate-400'
                          }`}
                        >
                          {run.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-slate-400">{formatDate(run.started_at)}</td>
                      <td className="px-4 py-3">
                        <Link
                          to={`/results?project_id=${projectId}`}
                          className="text-sky-400 hover:underline"
                        >
                          View results
                        </Link>
                        <span className="mx-2 text-slate-600">·</span>
                        <button type="button" onClick={() => setActiveTab('artifacts')} className="text-sky-400 hover:underline">View artifacts</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {activeTab === 'artifacts' && (
        <ArtifactsTab apiBase={apiBase} projectId={projectId} runs={runs} />
      )}
    </div>
  )
}
