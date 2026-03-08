import { useState, useEffect } from 'react'
import { Loader2 } from 'lucide-react'

export default function RunTeleportation({ apiBase }) {
  const [backend, setBackend] = useState('sim')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [jobStatus, setJobStatus] = useState(null)

  const wsBase = apiBase ? apiBase.replace(/^http/, 'ws') : `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`

  useEffect(() => {
    if (!result?.job_id || !wsBase) return
    setJobStatus({ status: 'QUEUED' })
    const ws = new WebSocket(`${wsBase}/ws/job/${result.job_id}`)
    ws.onmessage = (ev) => {
      try {
        const d = JSON.parse(ev.data)
        setJobStatus(d)
        if (d.status === 'DONE' && d.result) setResult(prev => ({ ...prev, ...d.result, job_status: 'DONE' }))
        if (d.status === 'ERROR') setError(d.result?.error || d.error || 'Job failed')
      } catch (_) {}
    }
    ws.onerror = () => setJobStatus(prev => prev ? { ...prev, status: 'ERROR' } : null)
    return () => ws.close()
  }, [result?.job_id, wsBase])

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setResult(null)
    setError(null)
    setJobStatus(null)
    try {
      const r = await fetch(`${apiBase}/api/run/protocol`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ protocol: 'teleport', backend }),
      })
      const data = await r.json().catch(() => ({}))
      if (!r.ok) throw new Error(data.detail || r.statusText)
      setResult(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-slate-100">Teleportation</h1>
      <p className="text-sm text-slate-500">
        Run teleportation protocol on simulation or IBM hardware. Hardware runs return a job_id and stream status via WebSocket.
      </p>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="backend" className="mb-1.5 block text-sm font-medium text-slate-300">
            Backend
          </label>
          <select
            id="backend"
            value={backend}
            onChange={(e) => setBackend(e.target.value)}
            className="w-full max-w-xs rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-slate-100 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
          >
            <option value="sim">Simulation</option>
            <option value="hardware">IBM hardware</option>
          </select>
        </div>
        <button
          type="submit"
          disabled={loading}
          className="inline-flex items-center gap-2 rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-offset-2 focus:ring-offset-slate-900 disabled:opacity-60"
        >
          {loading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              Running…
            </>
          ) : (
            'Run teleportation'
          )}
        </button>
      </form>

      {error && <p className="text-sm text-red-400">{error}</p>}
      {jobStatus && (
        <p className="text-sm text-slate-400">
          Job status: <strong className="text-slate-200">{jobStatus.status}</strong>
        </p>
      )}
      {result && (
        <section className="rounded-xl border border-slate-700/60 bg-slate-800/60 p-4">
          <h2 className="text-lg font-medium text-slate-100">Result</h2>
          <pre className="mt-2 overflow-auto rounded-lg bg-slate-900/80 p-4 text-sm text-slate-300">
            {JSON.stringify(result, null, 2)}
          </pre>
        </section>
      )}
    </div>
  )
}
