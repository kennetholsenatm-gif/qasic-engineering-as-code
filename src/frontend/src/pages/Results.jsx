import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { FileBarChart, RefreshCw, FolderOpen, Box, Download } from 'lucide-react'
import PhaseViewer3D from './PhaseViewer3D'

function fetchLatest(apiBase, projectId) {
  const url = projectId != null ? `${apiBase}/api/results/latest?project_id=${projectId}` : `${apiBase}/api/results/latest`
  return fetch(url).then(async (r) => {
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText)
    return r.json()
  })
}

function fetchMlflowRuns(apiBase, experimentId) {
  const url = experimentId ? `${apiBase}/api/mlflow/runs?experiment_id=${experimentId}` : `${apiBase}/api/mlflow/runs`
  return fetch(url).then(async (r) => (!r.ok ? { runs: [] } : r.json()))
}

function StatCard({ label, value, sub }) {
  return (
    <div className="rounded-lg border border-slate-700/60 bg-slate-800/60 px-4 py-3">
      <div className="text-xs font-medium uppercase tracking-wider text-slate-500">{label}</div>
      <div className="mt-0.5 text-lg font-semibold text-slate-100">{value}</div>
      {sub != null && <div className="mt-0.5 text-sm text-slate-500">{sub}</div>}
    </div>
  )
}

function InverseSection({ inverse }) {
  if (!inverse || typeof inverse !== 'object') return null
  const { phase_min, phase_max, phase_mean, num_meta_atoms, device, phase_band_lo, phase_band_hi } = inverse
  const stats = [
    phase_min != null && { label: 'Phase min (rad)', value: Number(phase_min).toFixed(4) },
    phase_max != null && { label: 'Phase max (rad)', value: Number(phase_max).toFixed(4) },
    phase_mean != null && { label: 'Phase mean (rad)', value: Number(phase_mean).toFixed(4) },
    num_meta_atoms != null && { label: 'Meta-atoms', value: String(num_meta_atoms) },
    device != null && { label: 'Device', value: String(device) },
    phase_band_lo != null && phase_band_hi != null && {
      label: 'Phase band',
      value: `[${Number(phase_band_lo).toFixed(3)}, ${Number(phase_band_hi).toFixed(3)}] rad`,
    },
  ].filter(Boolean)

  return (
    <section className="rounded-xl border border-slate-700/60 bg-slate-800/60 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-medium text-slate-100">Inverse design</h2>
        <Link
          to="/phase-viewer"
          className="inline-flex items-center gap-1.5 rounded-lg border border-sky-500/50 bg-sky-500/10 px-3 py-1.5 text-sm text-sky-400 transition-colors hover:bg-sky-500/20"
        >
          <Box className="h-4 w-4" />
          View in Phase Viewer (3D)
        </Link>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        {stats.map(({ label, value }) => (
          <StatCard key={label} label={label} value={value} />
        ))}
      </div>
      <details className="mt-4">
        <summary className="cursor-pointer text-sm text-slate-500 hover:text-slate-400">Show raw JSON</summary>
        <pre className="mt-2 overflow-auto rounded-lg bg-slate-900/80 p-4 text-xs text-slate-400">
          {JSON.stringify(inverse, null, 2)}
        </pre>
      </details>
    </section>
  )
}

function RoutingSection({ routing }) {
  if (!routing || typeof routing !== 'object') return null
  const mapping = routing.mapping ?? routing.logical_to_physical
  const arr = Array.isArray(mapping) ? mapping : (mapping && [mapping]) || []
  const topology = routing.topology ?? routing.topology_name
  const cost = routing.cost ?? routing.energy

  return (
    <section className="rounded-xl border border-slate-700/60 bg-slate-800/60 p-4">
      <h2 className="text-lg font-medium text-slate-100">Routing</h2>
      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
        {topology != null && <StatCard label="Topology" value={String(topology)} />}
        {cost != null && <StatCard label="Cost / energy" value={typeof cost === 'number' ? cost.toFixed(4) : String(cost)} />}
      </div>
      {arr.length > 0 && (
        <div className="mt-4">
          <h3 className="text-sm font-medium text-slate-400">Mapping</h3>
          <div className="mt-2 overflow-x-auto rounded-lg border border-slate-700/60">
            <table className="w-full min-w-[200px] border-collapse text-sm">
              <thead>
                <tr className="border-b border-slate-700 bg-slate-800/80">
                  {Object.keys(arr[0]).map((k) => (
                    <th key={k} className="px-3 py-2 text-left font-medium text-slate-400">{k}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {arr.slice(0, 20).map((row, i) => (
                  <tr key={i} className="border-b border-slate-700/60 hover:bg-slate-800/40">
                    {Object.values(row).map((v, j) => (
                      <td key={j} className="px-3 py-2 text-slate-300">{String(v)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            {arr.length > 20 && (
              <div className="px-3 py-2 text-xs text-slate-500">Showing first 20 of {arr.length} rows</div>
            )}
          </div>
        </div>
      )}
      <details className="mt-4">
        <summary className="cursor-pointer text-sm text-slate-500 hover:text-slate-400">Show raw JSON</summary>
        <pre className="mt-2 overflow-auto rounded-lg bg-slate-900/80 p-4 text-xs text-slate-400">
          {JSON.stringify(routing, null, 2)}
        </pre>
      </details>
    </section>
  )
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-600 bg-slate-800/30 py-16 px-6 text-center">
      <FolderOpen className="h-14 w-14 text-slate-500" aria-hidden />
      <p className="mt-4 text-slate-400">No results yet.</p>
      <p className="mt-1 text-sm text-slate-500">Run the pipeline or routing + inverse design to see results here.</p>
      <Link
        to="/run/pipeline"
        className="mt-6 inline-flex items-center gap-2 rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-sky-500"
      >
        Run pipeline
      </Link>
    </div>
  )
}

function GdsDownload({ apiBase, gdsPath }) {
  if (!gdsPath) return null
  const href = `${apiBase.replace(/\/$/, '')}/api/results/gds`
  return (
    <a
      href={href}
      download
      className="inline-flex items-center gap-2 rounded-lg border border-sky-500/50 bg-sky-500/10 px-3 py-2 text-sm text-sky-400 transition-colors hover:bg-sky-500/20"
    >
      <Download className="h-4 w-4" />
      Download GDS
    </a>
  )
}

function MlflowSection({ apiBase, experimentId }) {
  const { data } = useQuery({
    queryKey: ['mlflow-runs', apiBase, experimentId],
    queryFn: () => fetchMlflowRuns(apiBase, experimentId),
    staleTime: 30_000,
  })
  const runs = data?.runs || []
  if (!runs.length) return null
  return (
    <section className="rounded-xl border border-slate-700/60 bg-slate-800/60 p-4">
      <h2 className="text-lg font-medium text-slate-100">MLflow runs</h2>
      <div className="mt-3 overflow-x-auto">
        <table className="w-full min-w-[400px] border-collapse text-sm">
          <thead>
            <tr className="border-b border-slate-600 text-left text-slate-400">
              <th className="pb-2 pr-2">Run</th>
              <th className="pb-2 pr-2">Start</th>
              <th className="pb-2 pr-2">Metrics</th>
            </tr>
          </thead>
          <tbody>
            {runs.slice(0, 10).map((r) => (
              <tr key={r.run_id} className="border-b border-slate-700/60">
                <td className="py-2 pr-2 font-mono text-slate-300">{r.run_name || r.run_id?.slice(0, 8)}</td>
                <td className="py-2 pr-2 text-slate-500">{r.start_time ? new Date(r.start_time).toLocaleString() : '—'}</td>
                <td className="py-2 pr-2 text-slate-400">
                  {r.metrics && Object.keys(r.metrics).length ? (
                    <span>{Object.entries(r.metrics).map(([k, v]) => `${k}=${v}`).join(', ')}</span>
                  ) : (
                    '—'
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

export default function Results({ apiBase, projectId = null }) {
  const { data, error, isLoading, isRefetching, refetch } = useQuery({
    queryKey: ['results', 'latest', apiBase, projectId],
    queryFn: () => fetchLatest(apiBase, projectId),
    staleTime: 15_000,
    refetchInterval: 30_000,
  })

  if (error) {
    return (
      <div className="rounded-lg border border-red-900/50 bg-red-950/20 px-4 py-3 text-red-400">
        {error.message}
      </div>
    )
  }
  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-slate-500">
        <RefreshCw className="h-4 w-4 animate-spin" />
        Loading…
      </div>
    )
  }

  const hasData = data?.routing || data?.inverse

  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="flex items-center gap-2 text-2xl font-semibold text-slate-100">
          <FileBarChart className="h-7 w-7 text-sky-400" />
          Last results
        </h1>
        <div className="flex items-center gap-2">
          <GdsDownload apiBase={apiBase} gdsPath={data?.gds_path} />
          <button
            type="button"
            onClick={() => refetch()}
            disabled={isRefetching}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-sm text-slate-300 transition-colors hover:bg-slate-700 disabled:opacity-60"
          >
            <RefreshCw className={`h-4 w-4 ${isRefetching ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>
      {isRefetching && <p className="mt-1 text-sm text-slate-500">Refreshing…</p>}
      {!hasData && <EmptyState />}

      {hasData && (
        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <div className="rounded-xl border border-slate-700/60 bg-slate-800/60 p-4">
            <div className="flex items-center justify-between gap-2">
              <h2 className="text-lg font-medium text-slate-100">Phase viewer (3D)</h2>
              <Link
                to="/phase-viewer"
                className="text-sm text-sky-400 hover:underline"
              >
                Open full page
              </Link>
            </div>
            <div className="mt-3 min-h-[280px]">
              <PhaseViewer3D apiBase={apiBase} />
            </div>
          </div>
          <div>
            <MlflowSection apiBase={apiBase} />
          </div>
        </div>
      )}

      {data?.routing && <div className="mt-6"><RoutingSection routing={data.routing} /></div>}
      {data?.inverse && <div className="mt-6"><InverseSection inverse={data.inverse} /></div>}
    </>
  )
}
