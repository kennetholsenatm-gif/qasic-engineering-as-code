import { useState, useEffect } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'

const POLL_INTERVAL_MS = 2000

function fetchTask(apiBase, taskId) {
  return fetch(`${apiBase}/api/tasks/${taskId}`).then(async (r) => {
    const data = await r.json().catch(() => ({}))
    if (!r.ok) return { status: 'FAILURE', error: data.detail || r.statusText }
    return data
  })
}

export default function RunPipeline({ apiBase }) {
  const [backend, setBackend] = useState('sim')
  const [fast, setFast] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [taskId, setTaskId] = useState(null)

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
      if (data.taskId) setTaskId(data.taskId)
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

  const loading = submitMutation.isPending || (!!taskId && taskStatus !== 'error')
  const statusLabel = taskId ? (taskData?.status === 'PENDING' ? 'In queue' : taskData?.status === 'STARTED' ? 'Running…' : 'Polling…') : 'Running…'

  function handleSubmit(e) {
    e.preventDefault()
    setResult(null)
    setError(null)
    setTaskId(null)
    submitMutation.mutate({ backend, fast })
  }

  return (
    <>
      <h1 className="text-2xl font-semibold text-slate-100">Run full pipeline</h1>
      <p className="mt-1 text-sm text-slate-500">
        Pipeline runs on a Celery worker when available (routing + inverse); otherwise runs in the API.
      </p>
      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
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
          <label htmlFor="fast" className="text-sm text-slate-300">Fast</label>
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
      {taskId && !result && !error && (
        <div className="mt-4 flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800/60 px-4 py-3 text-sm text-slate-400">
          <Loader2 className="h-4 w-4 animate-spin shrink-0" />
          <span>Task ID: {taskId} — {statusLabel}</span>
        </div>
      )}
      {error && (
        <p className="mt-4 text-sm text-red-400">{error}</p>
      )}
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
