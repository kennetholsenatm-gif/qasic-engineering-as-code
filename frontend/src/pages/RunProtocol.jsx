import { useState } from 'react'

export default function RunProtocol({ apiBase }) {
  const [protocol, setProtocol] = useState('teleport')
  const [backend, setBackend] = useState('sim')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setResult(null)
    setError(null)
    try {
      const r = await fetch(`${apiBase}/api/run/protocol`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ protocol, backend }),
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
