import { useState } from 'react'
import { Loader2 } from 'lucide-react'

export default function RunQKD({ apiBase }) {
  const [protocol, setProtocol] = useState('bb84')
  const [nBits, setNBits] = useState(64)
  const [nTrials, setNTrials] = useState(500)
  const [seed, setSeed] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setResult(null)
    setError(null)
    try {
      const body = {
        protocol,
        n_bits: protocol === 'bb84' ? nBits : undefined,
        n_trials: protocol === 'e91' ? nTrials : undefined,
        seed: seed !== '' ? Number(seed) : undefined,
      }
      const r = await fetch(`${apiBase}/api/run/qkd`, {
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
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-slate-100">QKD (BB84 / E91)</h1>
      <p className="text-sm text-slate-500">
        Run pedagogical QKD in simulation. BB84 uses n_bits; E91 uses n_trials.
      </p>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="protocol" className="mb-1.5 block text-sm font-medium text-slate-300">
            Protocol
          </label>
          <select
            id="protocol"
            value={protocol}
            onChange={(e) => setProtocol(e.target.value)}
            className="w-full max-w-xs rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-slate-100 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
          >
            <option value="bb84">BB84</option>
            <option value="e91">E91</option>
          </select>
        </div>
        {protocol === 'bb84' && (
          <div>
            <label htmlFor="n_bits" className="mb-1.5 block text-sm font-medium text-slate-300">
              n_bits
            </label>
            <input
              id="n_bits"
              type="number"
              min={1}
              max={10000}
              value={nBits}
              onChange={(e) => setNBits(Number(e.target.value))}
              className="w-full max-w-xs rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-slate-100 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
            />
          </div>
        )}
        {protocol === 'e91' && (
          <div>
            <label htmlFor="n_trials" className="mb-1.5 block text-sm font-medium text-slate-300">
              n_trials
            </label>
            <input
              id="n_trials"
              type="number"
              min={1}
              max={100000}
              value={nTrials}
              onChange={(e) => setNTrials(Number(e.target.value))}
              className="w-full max-w-xs rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-slate-100 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
            />
          </div>
        )}
        <div>
          <label htmlFor="seed" className="mb-1.5 block text-sm font-medium text-slate-300">
            Seed (optional)
          </label>
          <input
            id="seed"
            type="number"
            value={seed}
            onChange={(e) => setSeed(e.target.value)}
            placeholder="Leave empty for random"
            className="w-full max-w-xs rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-slate-100 placeholder:text-slate-500 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="inline-flex items-center gap-2 rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-offset-2 focus:ring-offset-slate-900 disabled:opacity-60"
        >
          {loading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              Running…
            </>
          ) : (
            'Run QKD'
          )}
        </button>
      </form>

      {error && <p className="text-sm text-red-400">{error}</p>}
      {result && (
        <section className="rounded-xl border border-slate-700/60 bg-slate-800/60 p-4">
          <h2 className="text-lg font-medium text-slate-100">Result</h2>
          <pre className="mt-2 overflow-auto rounded-lg bg-slate-900/80 p-4 text-sm text-slate-300">
            {JSON.stringify(result, null, 2)}
          </pre>
        </section>
      )}
    </div>
  )
}
