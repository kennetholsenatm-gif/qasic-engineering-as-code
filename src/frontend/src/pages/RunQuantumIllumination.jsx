import { useState } from 'react'

export default function RunQuantumIllumination({ apiBase }) {
  const [eta, setEta] = useState(0.1)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setResult(null)
    setError(null)
    try {
      const r = await fetch(`${apiBase}/api/run/quantum-illumination`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ eta: Number(eta) }),
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
      <h1>DV Quantum Illumination</h1>
      <p className="muted">Compare entangled (Bell) vs unentangled (|1⟩) probe: thermal loss channel, Chernoff exponent.</p>
      <form onSubmit={handleSubmit}>
        <label>
          Reflectivity η (0–1)
          <input
            type="number"
            min={0}
            max={1}
            step={0.01}
            value={eta}
            onChange={e => setEta(e.target.value)}
          />
        </label>
        <button type="submit" disabled={loading}>{loading ? 'Running…' : 'Run'}</button>
      </form>
      {error && <p className="error">{error}</p>}
      {result && (
        <section className="card">
          <h2>Result (η = {result.eta})</h2>
          <table>
            <thead>
              <tr><th/> <th>P_err</th> <th>Chernoff exponent</th></tr>
            </thead>
            <tbody>
              <tr>
                <td>Entangled (Bell)</td>
                <td>{result.entangled.P_err.toFixed(6)}</td>
                <td>{result.entangled.chernoff_exponent.toFixed(6)}</td>
              </tr>
              <tr>
                <td>Unentangled (|1⟩)</td>
                <td>{result.unentangled.P_err.toFixed(6)}</td>
                <td>{result.unentangled.chernoff_exponent.toFixed(6)}</td>
              </tr>
            </tbody>
          </table>
          <p><strong>Advantage:</strong> P_err lower by {result.advantage.P_err_lower_by.toFixed(6)}, Chernoff higher by {result.advantage.chernoff_higher_by.toFixed(6)}</p>
        </section>
      )}
    </>
  )
}
