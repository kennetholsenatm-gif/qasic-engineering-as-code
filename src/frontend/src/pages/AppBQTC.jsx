import { useState } from 'react'
import { Loader2 } from 'lucide-react'
import { Link } from 'react-router-dom'

export default function AppBQTC({ apiBase }) {
  const [dryRun, setDryRun] = useState(true)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setResult(null)
    setError(null)
    try {
      const r = await fetch(`${apiBase}/api/apps/bqtc/run-cycle`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dry_run: dryRun }),
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
      <h1 className="text-2xl font-semibold text-slate-100">BQTC (Terrestrial Backhaul)</h1>
      <p className="text-sm text-slate-500">
        Run one BQTC pipeline cycle (no live telemetry; buffer may be empty). Full pipeline: <code className="rounded bg-slate-700 px-1 py-0.5 text-slate-300">cd apps/bqtc &amp;&amp; python pipeline.py</code>.
      </p>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="dry_run"
            checked={dryRun}
            onChange={(e) => setDryRun(e.target.checked)}
            className="h-4 w-4 rounded border-slate-600 bg-slate-800 text-sky-500 focus:ring-sky-500"
          />
          <label htmlFor="dry_run" className="text-sm text-slate-300">
            Dry run
          </label>
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
            'Run one cycle'
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

      <p className="text-xs text-slate-500">
        See also <Link to="/applications" className="text-sky-400 hover:underline">Applications</Link> for a combined BQTC + QRNC view.
      </p>
    </div>
  )
}
