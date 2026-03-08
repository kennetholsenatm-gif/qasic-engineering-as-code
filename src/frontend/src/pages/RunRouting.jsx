import { useState } from 'react'

export default function RunRouting({ apiBase }) {
  const [backend, setBackend] = useState('sim')
  const [fast, setFast] = useState(false)
  const [topology, setTopology] = useState('')
  const [qubits, setQubits] = useState('')
  const [hub, setHub] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setResult(null)
    setError(null)
    const body = { backend, fast }
    if (topology) body.topology = topology
    const q = parseInt(qubits, 10)
    if (topology && !isNaN(q) && q >= 2) body.qubits = q
    const h = parseInt(hub, 10)
    if (topology === 'star' && !isNaN(h) && h >= 0) body.hub = h
    try {
      const r = await fetch(`${apiBase}/api/run/routing`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
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
      <h1>Run routing</h1>
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
          Fast (affordable, &lt;5 min QPU)
        </label>
        <label>
          Topology (optional)
          <select value={topology} onChange={e => setTopology(e.target.value)}>
            <option value="">default (linear)</option>
            <option value="linear_chain">linear_chain</option>
            <option value="star">star</option>
            <option value="repeater_chain">repeater_chain</option>
          </select>
        </label>
        {topology && (
          <>
            <label>Qubits <input type="number" min={2} max={8} value={qubits} onChange={e => setQubits(e.target.value)} placeholder="3" /></label>
            {topology === 'star' && <label>Hub index <input type="number" min={0} value={hub} onChange={e => setHub(e.target.value)} placeholder="0" /></label>}
          </>
        )}
        <button type="submit" disabled={loading}>{loading ? 'Running…' : 'Run'}</button>
      </form>
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
