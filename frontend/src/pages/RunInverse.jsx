import { useState } from 'react'

export default function RunInverse({ apiBase }) {
  const [phaseBand, setPhaseBand] = useState('')
  const [routingPath, setRoutingPath] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setResult(null)
    setError(null)
    try {
      const r = await fetch(`${apiBase}/api/run/inverse`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          phase_band: phaseBand || null,
          routing_result_path: routingPath || null,
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
      <h1>Inverse design</h1>
      <form onSubmit={handleSubmit}>
        <label>
          Phase band (optional)
          <select value={phaseBand} onChange={e => setPhaseBand(e.target.value)}>
            <option value="">Full [0, 2π]</option>
            <option value="pi">π ± 0.14 rad (Cryo-CMOS)</option>
          </select>
        </label>
        <label>
          Routing result path (optional)
          <input type="text" value={routingPath} onChange={e => setRoutingPath(e.target.value)} placeholder="path to routing JSON" />
        </label>
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
