import { useState, useEffect, useRef } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Loader2, Terminal } from 'lucide-react'
import PipelineDag from '../components/PipelineDag'

const POLL_INTERVAL_MS = 2000

function fetchTask(apiBase, taskId) {
  return fetch(`${apiBase}/api/tasks/${taskId}`).then(async (r) => {
    const data = await r.json().catch(() => ({}))
    if (!r.ok) return { status: 'FAILURE', error: data.detail || r.statusText }
    return data
  })
}

function fetchProjects(apiBase) {
  return fetch(`${apiBase}/api/projects`).then(async (r) => {
    if (!r.ok) return { projects: [] }
    const d = await r.json()
    return d
  })
}

export default function RunPipeline({ apiBase }) {
  const [backend, setBackend] = useState('sim')
  const [fast, setFast] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [taskId, setTaskId] = useState(null)
  const [projectId, setProjectId] = useState(null)
  const [logLines, setLogLines] = useState([])
  const logEndRef = useRef(null)
  const eventSourceRef = useRef(null)

  const { data: projectsData } = useQuery({
    queryKey: ['projects', apiBase],
    queryFn: () => fetchProjects(apiBase),
    staleTime: 30_000,
  })
  const projects = projectsData?.projects || []

  const submitMutation = useMutation({
    mutationFn: async (body) => {
      const asyncRes = await fetch(`${apiBase}/api/run/pipeline/async`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const asyncData = await asyncRes.json().catch(() => ({}))
      if (asyncRes.ok && asyncData.task_id) return { taskId: asyncData.task_id }
      const syncRes = await fetch(`${apiBase}/api/run/pipeline`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const syncData = await syncRes.json().catch(() => ({}))
      if (!syncRes.ok) throw new Error(syncData.detail || syncRes.statusText)
      return { result: syncData }
    },
    onSuccess: (data) => {
      setError(null)
      if (data.taskId) {
        setTaskId(data.taskId)
        setLogLines([])
      }
      if (data.result) setResult(data.result)
    },
    onError: (err) => setError(err.message),
  })

  const { data: taskData, status: taskStatus } = useQuery({
    queryKey: ['task', apiBase, taskId],
    queryFn: () => fetchTask(apiBase, taskId),
    enabled: !!taskId,
    refetchInterval: (query) => {
      const d = query.state.data
      if (d?.status === 'SUCCESS' || d?.status === 'FAILURE') return false
      return POLL_INTERVAL_MS
    },
    refetchIntervalInBackground: true,
  })

  useEffect(() => {
    if (!taskId || !taskData) return
    if (taskData.status === 'SUCCESS' && taskData.result) {
      setResult(taskData.result)
      setTaskId(null)
    }
    if (taskData.status === 'FAILURE') {
      setError(taskData.error || 'Pipeline failed')
      setTaskId(null)
    }
  }, [taskId, taskData])

  useEffect(() => {
    if (!taskId || !apiBase) return
    const url = `${apiBase.replace(/\/$/, '')}/api/tasks/${taskId}/stream`
    const es = new EventSource(url)
    eventSourceRef.current = es
    es.onmessage = (ev) => {
      try {
        const payload = JSON.parse(ev.data)
        setLogLines((prev) => [...prev, payload.message || ev.data])
        if (payload.done) es.close()
      } catch {
        setLogLines((prev) => [...prev, ev.data])
      }
    }
    es.onerror = () => es.close()
    return () => {
      es.close()
      eventSourceRef.current = null
    }
  }, [taskId, apiBase])

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logLines])

  const loading = submitMutation.isPending || (!!taskId && taskStatus !== 'error')
  const statusLabel = taskId
    ? taskData?.status === 'PENDING'
      ? 'In queue'
      : taskData?.status === 'STARTED'
        ? 'Running…'
        : 'Polling…'
    : 'Running…'

  function handleSubmit(e) {
    e.preventDefault()
    setResult(null)
    setError(null)
    setTaskId(null)
    submitMutation.mutate({
      backend,
      fast,
      project_id: projectId || undefined,
    })
  }

  const activeStep = taskData?.status === 'STARTED' ? 'routing' : null

  return (
    <>
      <h1 className="text-2xl font-semibold text-slate-100">Run full pipeline</h1>
      <p className="mt-1 text-sm text-slate-500">
        Pipeline runs on a Celery worker when available (routing + inverse); otherwise runs in the API.
      </p>

      <section className="mt-6">
        <h2 className="mb-2 text-sm font-medium text-slate-400">Pipeline DAG</h2>
        <PipelineDag apiBase={apiBase} activeStep={activeStep} />
      </section>

      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        {projects.length > 0 && (
          <div>
            <label htmlFor="project" className="mb-1.5 block text-sm font-medium text-slate-300">
              Project (optional)
            </label>
            <select
              id="project"
              value={projectId ?? ''}
              onChange={(e) => setProjectId(e.target.value ? Number(e.target.value) : null)}
              className="w-full max-w-xs rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-slate-100 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
            >
              <option value="">— None —</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>
        )}
        <div>
          <label htmlFor="backend" className="mb-1.5 block text-sm font-medium text-slate-300">
            Backend
          </label>
          <select
            id="backend"
            value={backend}
            onChange={(e) => setBackend(e.target.value)}
            className="w-full max-w-xs rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-slate-100 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500 disabled:opacity-60"
          >
            <option value="sim">Simulation</option>
            <option value="hardware">IBM hardware</option>
          </select>
        </div>
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="fast"
            checked={fast}
            onChange={(e) => setFast(e.target.checked)}
            className="h-4 w-4 rounded border-slate-600 bg-slate-800 text-sky-500 focus:ring-sky-500"
          />
          <label htmlFor="fast" className="text-sm text-slate-300">
            Fast
          </label>
        </div>
        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-offset-2 focus:ring-offset-slate-900 disabled:opacity-60 disabled:hover:bg-sky-600"
          >
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                {statusLabel}
              </>
            ) : (
              'Run pipeline'
            )}
          </button>
        </div>
      </form>

      {taskId && (logLines.length > 0 || !taskData?.result) && (
        <div className="mt-4 rounded-xl border border-slate-700 bg-slate-900/80 overflow-hidden">
          <div className="flex items-center gap-2 border-b border-slate-700 bg-slate-800/60 px-3 py-2 text-sm text-slate-400">
            <Terminal className="h-4 w-4" />
            Live log (task: {taskId})
          </div>
          <div className="max-h-48 overflow-y-auto p-3 font-mono text-xs text-slate-300 whitespace-pre-wrap">
            {logLines.length ? logLines.map((line, i) => <div key={i}>{line}</div>) : 'Waiting for output…'}
            <div ref={logEndRef} />
          </div>
        </div>
      )}

      {taskId && !result && !error && logLines.length === 0 && (
        <div className="mt-4 flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800/60 px-4 py-3 text-sm text-slate-400">
          <Loader2 className="h-4 w-4 animate-spin shrink-0" />
          <span>Task ID: {taskId} — {statusLabel}</span>
        </div>
      )}
      {error && <p className="mt-4 text-sm text-red-400">{error}</p>}
      {result && (
        <section className="mt-6 rounded-xl border border-slate-700/60 bg-slate-800/60 p-4">
          <h2 className="text-lg font-medium text-slate-100">Result</h2>
          <pre className="mt-2 overflow-auto rounded-lg bg-slate-900/80 p-4 text-sm text-slate-300">
            {JSON.stringify(result, null, 2)}
          </pre>
        </section>
      )}
    </>
  )
}
