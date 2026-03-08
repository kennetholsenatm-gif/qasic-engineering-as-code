import { useState } from 'react'

export default function Applications({ apiBase }) {
  const [qrncMint, setQrncMint] = useState(null)
  const [qrncMintLoading, setQrncMintLoading] = useState(false)
  const [bqtcResult, setBqtcResult] = useState(null)
  const [bqtcLoading, setBqtcLoading] = useState(false)

  const handleMint = () => {
    setQrncMintLoading(true)
    setQrncMint(null)
    fetch(`${apiBase}/api/apps/qrnc/mint`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ num_bytes: 32, use_real_hardware: false }),
    })
      .then(r => r.json())
      .then(d => setQrncMint(d))
      .catch(e => setQrncMint({ error: e.message }))
      .finally(() => setQrncMintLoading(false))
  }

  const handleBqtcCycle = () => {
    setBqtcLoading(true)
    setBqtcResult(null)
    fetch(`${apiBase}/api/apps/bqtc/run-cycle`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    })
      .then(r => r.json())
      .then(d => setBqtcResult(d))
      .catch(e => setBqtcResult({ error: e.message }))
      .finally(() => setBqtcLoading(false))
  }

  return (
    <>
      <h1>Applications</h1>
      <p>BQTC (Bayesian-Quantum Traffic Controller) and QRNC (quantum-backed tokens and exchange) run from <code>apps/</code>. See <a href={`${apiBase}/docs/docs/APPLICATIONS.md`} target="_blank" rel="noopener noreferrer">docs/APPLICATIONS.md</a> for details.</p>

      <section>
        <h2>QRNC — Quantum-backed tokens</h2>
        <p>Mint a token with quantum entropy (simulator). For two-party exchange, use <code>POST /api/apps/qrnc/exchange</code> with two token hexes.</p>
        <button onClick={handleMint} disabled={qrncMintLoading}>
          {qrncMintLoading ? 'Minting…' : 'Mint token (sim)'}
        </button>
        {qrncMint && (
          <pre style={{ marginTop: '0.5rem', fontSize: '0.9rem', overflow: 'auto' }}>
            {qrncMint.error ? String(qrncMint.error) : JSON.stringify(qrncMint, null, 2)}
          </pre>
        )}
      </section>

      <section>
        <h2>BQTC — One cycle</h2>
        <p>Run one pipeline cycle (no live telemetry; buffer may be empty). Full pipeline: <code>cd apps/bqtc && python pipeline.py</code>.</p>
        <button onClick={handleBqtcCycle} disabled={bqtcLoading}>
          {bqtcLoading ? 'Running…' : 'Run one cycle'}
        </button>
        {bqtcResult && (
          <pre style={{ marginTop: '0.5rem', fontSize: '0.9rem', overflow: 'auto' }}>
            {bqtcResult.error ? String(bqtcResult.error) : JSON.stringify(bqtcResult, null, 2)}
          </pre>
        )}
      </section>
    </>
  )
}
