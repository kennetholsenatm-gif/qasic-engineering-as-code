import { useState, useEffect } from 'react'

export default function RunProtocol({ apiBase }) {
  const [protocol, setProtocol] = useState('teleport')
  const [backend, setBackend] = useState('sim')
  const [useCircuitFunction, setUseCircuitFunction] = useState(false)
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
        body: JSON.stringify({
          protocol,
          backend,
          use_circuit_function: backend === 'hardware' && useCircuitFunction,
        }),
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
    <>
      <h1>Run protocol</h1>
      <form onSubmit={handleSubmit}>
        <label>
          Protocol
          <select value={protocol} onChange={e => setProtocol(e.target.value)}>
            <option value="teleport">Teleport</option>
            <option value="bell">Bell</option>
            <option value="commitment">Commitment</option>
            <option value="thief">Thief</option>
          </select>
        </label>
        <label>
          Backend
          <select value={backend} onChange={e => setBackend(e.target.value)}>
            <option value="sim">Simulation</option>
            <option value="hardware">IBM hardware</option>
          </select>
        </label>
        {backend === 'hardware' && (
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <input
              type="checkbox"
              checked={useCircuitFunction}
              onChange={e => setUseCircuitFunction(e.target.checked)}
            />
            Use Qiskit Circuit Function (error mitigation, workload summary)
          </label>
        )}
        <button type="submit" disabled={loading}>{loading ? 'Running…' : 'Run'}</button>
      </form>
      {error && <p className="error">{error}</p>}
      {jobStatus && (
        <p className="job-status">Job status: <strong>{jobStatus.status}</strong></p>
      )}
      {result && (
        <section className="card">
          <h2>Result</h2>
          {result.resource_usage && (
            <div className="workload-summary" style={{ marginBottom: '1rem' }}>
              <h3>Workload summary</h3>
              <p className="muted">CPU/QPU time by stage (e.g. from Qiskit Functions)</p>
              <ul style={{ listStyle: 'none', paddingLeft: 0 }}>
                {Object.entries(result.resource_usage).map(([stage, usage]) => (
                  <li key={stage}>
                    <strong>{stage}</strong>: {typeof usage === 'object' && usage !== null
                      ? Object.entries(usage).map(([k, v]) => `${k}: ${v}`).join(', ')
                      : String(usage)}
                  </li>
                ))}
              </ul>
            </div>
          )}
          <pre>{JSON.stringify(result, null, 2)}</pre>
        </section>
      )}
    </>
  )
}
