import { useState } from 'react'

export default function RunQuantumRadar({ apiBase }) {
  const [mode, setMode] = useState('single') // single | sweep | optimize
  const [eta, setEta] = useState(0.2)
  const [n_b, setN_b] = useState(2)
  const [r, setR] = useState(1.0)
  const [sweepParam, setSweepParam] = useState('r')
  const [sweepMin, setSweepMin] = useState(0.2)
  const [sweepMax, setSweepMax] = useState(1.2)
  const [sweepSteps, setSweepSteps] = useState(11)
  const [optParam, setOptParam] = useState('r')
  const [optMin, setOptMin] = useState(0.1)
  const [optMax, setOptMax] = useState(2.0)
  const [optSteps, setOptSteps] = useState(30)
  const [maximize, setMaximize] = useState('mutual_info')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  async function handleSingle(e) {
    e.preventDefault()
    setLoading(true)
    setResult(null)
    setError(null)
    try {
      const res = await fetch(`${apiBase}/api/run/quantum-radar`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ eta: Number(eta), n_b: Number(n_b), r: Number(r) }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data.detail || res.statusText)
      setResult({ mode: 'single', data })
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleSweep(e) {
    e.preventDefault()
    setLoading(true)
    setResult(null)
    setError(null)
    try {
      const res = await fetch(`${apiBase}/api/run/quantum-radar/sweep`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          param: sweepParam,
          min_val: Number(sweepMin),
          max_val: Number(sweepMax),
          steps: Number(sweepSteps),
          eta: Number(eta),
          n_b: Number(n_b),
          r: Number(r),
        }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data.detail || res.statusText)
      setResult({ mode: 'sweep', data })
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleOptimize(e) {
    e.preventDefault()
    setLoading(true)
    setResult(null)
    setError(null)
    try {
      const res = await fetch(`${apiBase}/api/run/quantum-radar/optimize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          param: optParam,
          optimize_min: Number(optMin),
          optimize_max: Number(optMax),
          steps: Number(optSteps),
          eta: Number(eta),
          n_b: Number(n_b),
          r: Number(r),
          maximize,
        }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data.detail || res.statusText)
      setResult({ mode: 'optimize', data })
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <h1>CV Quantum Radar</h1>
      <p className="muted">TMSV + lossy thermal beam splitter: mutual information and SNR proxy (H1 vs H0).</p>

      <div className="tabs">
        <button type="button" className={mode === 'single' ? 'active' : ''} onClick={() => setMode('single')}>Single run</button>
        <button type="button" className={mode === 'sweep' ? 'active' : ''} onClick={() => setMode('sweep')}>Sweep</button>
        <button type="button" className={mode === 'optimize' ? 'active' : ''} onClick={() => setMode('optimize')}>Optimize</button>
      </div>

      {mode === 'single' && (
        <form onSubmit={handleSingle}>
          <label>η <input type="number" min={0} max={1} step={0.01} value={eta} onChange={e => setEta(e.target.value)} /></label>
          <label>n_b <input type="number" min={0} step={0.1} value={n_b} onChange={e => setN_b(e.target.value)} /></label>
          <label>r <input type="number" min={0} step={0.1} value={r} onChange={e => setR(e.target.value)} /></label>
          <button type="submit" disabled={loading}>{loading ? 'Running…' : 'Run'}</button>
        </form>
      )}

      {mode === 'sweep' && (
        <form onSubmit={handleSweep}>
          <label>Sweep <select value={sweepParam} onChange={e => setSweepParam(e.target.value)}>
            <option value="eta">eta</option>
            <option value="n_b">n_b</option>
            <option value="r">r</option>
          </select></label>
          <label>Min <input type="number" value={sweepMin} onChange={e => setSweepMin(e.target.value)} /></label>
          <label>Max <input type="number" value={sweepMax} onChange={e => setSweepMax(e.target.value)} /></label>
          <label>Steps <input type="number" min={2} max={200} value={sweepSteps} onChange={e => setSweepSteps(e.target.value)} /></label>
          <p className="muted">Fixed: η={eta}, n_b={n_b}, r={r}</p>
          <button type="submit" disabled={loading}>{loading ? 'Sweeping…' : 'Sweep'}</button>
        </form>
      )}

      {mode === 'optimize' && (
        <form onSubmit={handleOptimize}>
          <label>Optimize <select value={optParam} onChange={e => setOptParam(e.target.value)}>
            <option value="eta">eta</option>
            <option value="n_b">n_b</option>
            <option value="r">r</option>
          </select></label>
          <label>Min <input type="number" value={optMin} onChange={e => setOptMin(e.target.value)} /></label>
          <label>Max <input type="number" value={optMax} onChange={e => setOptMax(e.target.value)} /></label>
          <label>Steps <input type="number" min={5} max={200} value={optSteps} onChange={e => setOptSteps(e.target.value)} /></label>
          <label>Maximize <select value={maximize} onChange={e => setMaximize(e.target.value)}>
            <option value="mutual_info">Mutual info (H1)</option>
            <option value="snr">SNR proxy (H1)</option>
          </select></label>
          <p className="muted">Fixed: η={eta}, n_b={n_b}, r={r}</p>
          <button type="submit" disabled={loading}>{loading ? 'Optimizing…' : 'Optimize'}</button>
        </form>
      )}

      {error && <p className="error">{error}</p>}

      {result && result.mode === 'single' && (
        <section className="card">
          <h2>Result</h2>
          <p>H1 (target present): I(idler;return) = {result.data.mutual_info_H1?.toFixed(6)}, Var = {result.data.return_variance_H1?.toFixed(6)}, SNR proxy = {result.data.snr_proxy_H1?.toFixed(6)}</p>
          <p>H0 (target absent): I(idler;return) = {result.data.mutual_info_H0?.toFixed(6)}, Var = {result.data.return_variance_H0?.toFixed(6)}, SNR proxy = {result.data.snr_proxy_H0?.toFixed(6)}</p>
        </section>
      )}

      {result && result.mode === 'sweep' && (
        <section className="card">
          <h2>Sweep: {result.data.param}</h2>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>{result.data.param}</th>
                  <th>I_H1</th>
                  <th>Var_H1</th>
                  <th>SNR_H1</th>
                </tr>
              </thead>
              <tbody>
                {result.data.results?.slice(0, 25).map((row, i) => (
                  <tr key={i}>
                    <td>{Number(row[result.data.param]).toFixed(4)}</td>
                    <td>{Number(row.mutual_info_H1).toFixed(6)}</td>
                    <td>{Number(row.return_variance_H1).toFixed(4)}</td>
                    <td>{Number(row.snr_proxy_H1).toFixed(6)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {result.data.results?.length > 25 && <p className="muted">Showing first 25 of {result.data.results.length} rows.</p>}
        </section>
      )}

      {result && result.mode === 'optimize' && (
        <section className="card">
          <h2>Optimize</h2>
          <p><strong>Best {optParam}</strong> = {Number(result.data.best_value).toFixed(6)}</p>
          <p>mutual_info_H1 = {result.data.best_result?.mutual_info_H1?.toFixed(6)}, snr_proxy_H1 = {result.data.best_result?.snr_proxy_H1?.toFixed(6)}</p>
          <p>H1: Var = {result.data.best_result?.return_variance_H1?.toFixed(6)}</p>
        </section>
      )}
    </>
  )
}
