import { useState } from 'react'
import { Loader2 } from 'lucide-react'
import { Link } from 'react-router-dom'

export default function EngineeringHEaC({ apiBase }) {
  const [downloading, setDownloading] = useState(false)
  const [gdsError, setGdsError] = useState(null)

  async function handleDownloadGds() {
    setDownloading(true)
    setGdsError(null)
    try {
      const base = (apiBase || '').replace(/\/$/, '')
      const url = base ? `${base}/api/results/gds` : '/api/results/gds'
      const r = await fetch(url)
      if (!r.ok) {
        if (r.status === 404) throw new Error('No GDS file found. Run pipeline with HEaC and GDS first.')
        throw new Error(r.statusText || 'Download failed')
      }
      const blob = await r.blob()
      const disposition = r.headers.get('Content-Disposition')
      const filename = disposition?.match(/filename="?([^";]+)"?/)?.[1] || 'output.gds'
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = filename
      a.click()
      URL.revokeObjectURL(a.href)
    } catch (err) {
      setGdsError(err.message)
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-slate-100">HEaC DRC/LVS</h1>
      <p className="text-sm text-slate-500">
        Hardware Engineering as Code: phase-to-geometry manifest, GDS export, and optional DRC/LVS. The GDS file is produced when you run the pipeline with HEaC and GDS enabled.
      </p>

      <section className="rounded-xl border border-slate-700/60 bg-slate-800/40 p-4">
        <h2 className="mb-2 text-lg font-medium text-slate-100">Download latest GDS</h2>
        <p className="mb-3 text-sm text-slate-400">
          Download the most recent GDS file from the last pipeline run that included <code className="rounded bg-slate-700 px-1 py-0.5 text-slate-300">--heac --gds</code>.
        </p>
        <button
          type="button"
          onClick={handleDownloadGds}
          disabled={downloading}
          className="inline-flex items-center gap-2 rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-offset-2 focus:ring-offset-slate-900 disabled:opacity-60"
        >
          {downloading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              Downloading…
            </>
          ) : (
            'Download GDS'
          )}
        </button>
        {gdsError && <p className="mt-2 text-sm text-red-400">{gdsError}</p>}
      </section>

      <section className="rounded-xl border border-slate-700/60 bg-slate-800/40 p-4">
        <h2 className="mb-2 text-lg font-medium text-slate-100">Run pipeline with HEaC and GDS</h2>
        <p className="mb-3 text-sm text-slate-400">
          To generate a new GDS file, run the full pipeline with the HEaC option enabled (and GDS export). Then return here to download.
        </p>
        <Link
          to="/run/pipeline"
          className="inline-flex rounded-lg border border-slate-600 bg-slate-700 px-4 py-2 text-sm font-medium text-slate-200 hover:bg-slate-600 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-offset-2 focus:ring-offset-slate-900"
        >
          Open Run Pipeline
        </Link>
      </section>
    </div>
  )
}
