import { useState } from 'react'
import { Loader2 } from 'lucide-react'
import { Link } from 'react-router-dom'

export default function AppQRNC({ apiBase }) {
  const [numBytes, setNumBytes] = useState(32)
  const [useRealHardware, setUseRealHardware] = useState(false)
  const [mintLoading, setMintLoading] = useState(false)
  const [mintResult, setMintResult] = useState(null)
  const [mintError, setMintError] = useState(null)

  const [tokenAHex, setTokenAHex] = useState('')
  const [tokenBHex, setTokenBHex] = useState('')
  const [partyAId, setPartyAId] = useState('Alice')
  const [partyBId, setPartyBId] = useState('Bob')
  const [exchangeLoading, setExchangeLoading] = useState(false)
  const [exchangeResult, setExchangeResult] = useState(null)
  const [exchangeError, setExchangeError] = useState(null)

  async function handleMint(e) {
    e.preventDefault()
    setMintLoading(true)
    setMintResult(null)
    setMintError(null)
    try {
      const r = await fetch(`${apiBase}/api/apps/qrnc/mint`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ num_bytes: numBytes, use_real_hardware: useRealHardware }),
      })
      const data = await r.json().catch(() => ({}))
      if (!r.ok) throw new Error(data.detail || r.statusText)
      setMintResult(data)
    } catch (err) {
      setMintError(err.message)
    } finally {
      setMintLoading(false)
    }
  }

  async function handleExchange(e) {
    e.preventDefault()
    setExchangeLoading(true)
    setExchangeResult(null)
    setExchangeError(null)
    try {
      const r = await fetch(`${apiBase}/api/apps/qrnc/exchange`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          token_a_hex: tokenAHex.trim(),
          token_b_hex: tokenBHex.trim(),
          party_a_id: partyAId || 'Alice',
          party_b_id: partyBId || 'Bob',
        }),
      })
      const data = await r.json().catch(() => ({}))
      if (!r.ok) throw new Error(data.detail || r.statusText)
      setExchangeResult(data)
    } catch (err) {
      setExchangeError(err.message)
    } finally {
      setExchangeLoading(false)
    }
  }

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-semibold text-slate-100">QRNC</h1>
      <p className="text-sm text-slate-500">
        Quantum-backed tokens: mint with quantum entropy (sim or IBM), then run two-party exchange (commit-then-reveal).
      </p>

      <section className="rounded-xl border border-slate-700/60 bg-slate-800/40 p-4">
        <h2 className="mb-2 text-lg font-medium text-slate-100">Mint token</h2>
        <form onSubmit={handleMint} className="space-y-4">
          <div>
            <label htmlFor="num_bytes" className="mb-1.5 block text-sm font-medium text-slate-300">
              num_bytes
            </label>
            <input
              id="num_bytes"
              type="number"
              min={1}
              max={64}
              value={numBytes}
              onChange={(e) => setNumBytes(Number(e.target.value))}
              className="w-full max-w-xs rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-slate-100 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
            />
          </div>
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="use_real_hardware"
              checked={useRealHardware}
              onChange={(e) => setUseRealHardware(e.target.checked)}
              className="h-4 w-4 rounded border-slate-600 bg-slate-800 text-sky-500 focus:ring-sky-500"
            />
            <label htmlFor="use_real_hardware" className="text-sm text-slate-300">
              Use real IBM hardware
            </label>
          </div>
          <button
            type="submit"
            disabled={mintLoading}
            className="inline-flex items-center gap-2 rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-500 disabled:opacity-60"
          >
            {mintLoading ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : null}
            {mintLoading ? 'Minting…' : 'Mint token'}
          </button>
        </form>
        {mintError && <p className="mt-2 text-sm text-red-400">{mintError}</p>}
        {mintResult && (
          <pre className="mt-2 overflow-auto rounded-lg bg-slate-900/80 p-4 text-sm text-slate-300">
            {JSON.stringify(mintResult, null, 2)}
          </pre>
        )}
      </section>

      <section className="rounded-xl border border-slate-700/60 bg-slate-800/40 p-4">
        <h2 className="mb-2 text-lg font-medium text-slate-100">Two-party exchange</h2>
        <p className="mb-3 text-xs text-slate-500">
          Paste two token hex values (from mint or previous exchange) to run commit-then-reveal.
        </p>
        <form onSubmit={handleExchange} className="space-y-4">
          <div>
            <label htmlFor="token_a_hex" className="mb-1.5 block text-sm font-medium text-slate-300">
              Token A (hex)
            </label>
            <input
              id="token_a_hex"
              type="text"
              value={tokenAHex}
              onChange={(e) => setTokenAHex(e.target.value)}
              placeholder="e.g. from mint result value"
              className="w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 font-mono text-sm text-slate-100 placeholder:text-slate-500 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
            />
          </div>
          <div>
            <label htmlFor="token_b_hex" className="mb-1.5 block text-sm font-medium text-slate-300">
              Token B (hex)
            </label>
            <input
              id="token_b_hex"
              type="text"
              value={tokenBHex}
              onChange={(e) => setTokenBHex(e.target.value)}
              placeholder="e.g. from mint result value"
              className="w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 font-mono text-sm text-slate-100 placeholder:text-slate-500 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
            />
          </div>
          <div className="flex gap-4">
            <div>
              <label htmlFor="party_a_id" className="mb-1.5 block text-sm font-medium text-slate-300">
                Party A ID
              </label>
              <input
                id="party_a_id"
                type="text"
                value={partyAId}
                onChange={(e) => setPartyAId(e.target.value)}
                className="w-32 rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-slate-100 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
              />
            </div>
            <div>
              <label htmlFor="party_b_id" className="mb-1.5 block text-sm font-medium text-slate-300">
                Party B ID
              </label>
              <input
                id="party_b_id"
                type="text"
                value={partyBId}
                onChange={(e) => setPartyBId(e.target.value)}
                className="w-32 rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-slate-100 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
              />
            </div>
          </div>
          <button
            type="submit"
            disabled={exchangeLoading || !tokenAHex.trim() || !tokenBHex.trim()}
            className="inline-flex items-center gap-2 rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-500 disabled:opacity-60"
          >
            {exchangeLoading ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : null}
            {exchangeLoading ? 'Exchanging…' : 'Exchange'}
          </button>
        </form>
        {exchangeError && <p className="mt-2 text-sm text-red-400">{exchangeError}</p>}
        {exchangeResult && (
          <pre className="mt-2 overflow-auto rounded-lg bg-slate-900/80 p-4 text-sm text-slate-300">
            {JSON.stringify(exchangeResult, null, 2)}
          </pre>
        )}
      </section>

      <p className="text-xs text-slate-500">
        See also <Link to="/applications" className="text-sky-400 hover:underline">Applications</Link> for a combined BQTC + QRNC view.
      </p>
    </div>
  )
}
