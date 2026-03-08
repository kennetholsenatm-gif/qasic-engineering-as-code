import { useState, useRef } from 'react'

const POLL_INTERVAL_MS = 2000
const POLL_MAX_ATTEMPTS = 600 // ~20 min at 2s

export default function RunInverse({ apiBase }) {
  const [phaseBand, setPhaseBand] = useState('')
  const [routingPath, setRoutingPath] = useState('')
  const [model, setModel] = useState('mlp')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [status, setStatus] = useState(null) // 'idle' | 'queued' | 'polling' | 'done'
  const [taskId, setTaskId] = useState(null)
  const pollCountRef = useRef(0)

  async function pollTask(id) {
    const r = await fetch(`${apiBase}/api/tasks/${id}`)
    const data = await r.json().catch(() => ({}))
    if (!r.ok) return { status: 'FAILURE', error: data.detail || r.statusText }
    if (data.status === 'SUCCESS' && data.result) return { status: 'SUCCESS', result: data.result }
    if (data.status === 'FAILURE') return { status: 'FAILURE', error: data.error || 'Task failed' }
    return { status: data.status, result: data.result }
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setResult(null)
    setError(null)
    setStatus('idle')
    setTaskId(null)
    pollCountRef.current = 0

    const body = {
      phase_band: phaseBand || null,
      routing_result_path: routingPath || null,
      model: model || null,
    }

    try {
      // Prefer async (Celery): offload heavy inverse to worker, keep dashboard responsive
      const asyncRes = await fetch(`${apiBase}/api/run/inverse/async`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const asyncData = await asyncRes.json().catch(() => ({}))

      if (asyncRes.ok && asyncData.task_id) {
        setTaskId(asyncData.task_id)
        setStatus('queued')
        setStatus('polling')
        while (pollCountRef.current < POLL_MAX_ATTEMPTS) {
          pollCountRef.current += 1
          const pollResult = await pollTask(asyncData.task_id)
          if (pollResult.status === 'SUCCESS') {
            setResult(pollResult.result)
            setStatus('done')
            break
          }
          if (pollResult.status === 'FAILURE') {
            setError(pollResult.error || 'Inverse design failed')
            setStatus('done')
            break
          }
          await new Promise(r => setTimeout(r, POLL_INTERVAL_MS))
        }
        if (pollCountRef.current >= POLL_MAX_ATTEMPTS) {
          setError('Polling timed out. Check task status or results later.')
          setStatus('done')
        }
      } else {
        // Fallback: synchronous run (API runs inverse in-process)
        setStatus('polling')
        const r = await fetch(`${apiBase}/api/run/inverse`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        })
        const data = await r.json().catch(() => ({}))
        if (!r.ok) throw new Error(data.detail || r.statusText)
        setResult(data)
        setStatus('done')
      }
    } catch (err) {
      setError(err.message)
      setStatus('done')
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <h1>Inverse design</h1>
      <p className="muted">Heavy work (GNN/MLP) runs on a Celery worker when available; otherwise runs in the API.</p>
      <form onSubmit={handleSubmit}>
        <label>
          Phase band (optional)
          <select value={phaseBand} onChange={e => setPhaseBand(e.target.value)}>
            <option value="">Full [0, 2π]</option>
            <option value="pi">π ± 0.14 rad (Cryo-CMOS)</option>
          </select>
        </label>
        <label>
          Model
          <select value={model} onChange={e => setModel(e.target.value)}>
            <option value="mlp">MLP</option>
            <option value="gnn">GNN</option>
          </select>
        </label>
        <label>
          Routing result path (optional)
          <input type="text" value={routingPath} onChange={e => setRoutingPath(e.target.value)} placeholder="path to routing JSON" />
        </label>
        <button type="submit" disabled={loading}>
          {loading ? (status === 'polling' ? 'Running… (worker)' : 'Running…') : 'Run'}
        </button>
      </form>
      {taskId && status !== 'done' && <p className="muted">Task ID: {taskId} — polling for result…</p>}
      {error && <p className="error">{error}</p>}
      {result && (
        <section className="card">
          <h2>Result</h2>
          <pre>{JSON.stringify(result, null, 2)}</pre>
        </section>
      )}
    </>
  )
}
