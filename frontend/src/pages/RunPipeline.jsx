import { useState, useRef } from 'react'

const POLL_INTERVAL_MS = 2000
const POLL_MAX_ATTEMPTS = 900 // ~30 min at 2s

export default function RunPipeline({ apiBase }) {
  const [backend, setBackend] = useState('sim')
  const [fast, setFast] = useState(false)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [status, setStatus] = useState(null)
  const [taskId, setTaskId] = useState(null)
  const pollCountRef = useRef(0)

  async function pollTask(id) {
    const r = await fetch(`${apiBase}/api/tasks/${id}`)
    const data = await r.json().catch(() => ({}))
    if (!r.ok) return { status: 'FAILURE', error: data.detail || r.statusText }
    if (data.status === 'SUCCESS' && data.result) return { status: 'SUCCESS', result: data.result }
    if (data.status === 'FAILURE') return { status: 'FAILURE', error: data.error || 'Pipeline failed' }
    return { status: data.status, result: data.result }
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setResult(null)
    setError(null)
    setStatus(null)
    setTaskId(null)
    pollCountRef.current = 0

    const body = { backend, fast }

    try {
      // Prefer async (Celery): offload pipeline to worker so dashboard stays responsive
      const asyncRes = await fetch(`${apiBase}/api/run/pipeline/async`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const asyncData = await asyncRes.json().catch(() => ({}))

      if (asyncRes.ok && asyncData.task_id) {
        setTaskId(asyncData.task_id)
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
            setError(pollResult.error || 'Pipeline failed')
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
        // Fallback: synchronous run
        setStatus('polling')
        const r = await fetch(`${apiBase}/api/run/pipeline`, {
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
      <h1>Run full pipeline</h1>
      <p className="muted">Pipeline runs on a Celery worker when available (routing + inverse); otherwise runs in the API.</p>
      <form onSubmit={handleSubmit}>
        <label>
          Backend
          <select value={backend} onChange={e => setBackend(e.target.value)}>
            <option value="sim">Simulation</option>
            <option value="hardware">IBM hardware</option>
          </select>
        </label>
        <label>
          <input type="checkbox" checked={fast} onChange={e => setFast(e.target.checked)} />
          Fast
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
