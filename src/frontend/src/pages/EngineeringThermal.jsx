import { Link } from 'react-router-dom'

export default function EngineeringThermal({ apiBase }) {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-slate-100">Thermal & Packaging FEA</h1>
      <p className="text-sm text-slate-500">
        Thermal and packaging finite-element analysis runs as part of the pipeline. There is no dedicated run endpoint; use the main pipeline with the thermal stage enabled.
      </p>

      <section className="rounded-xl border border-slate-700/60 bg-slate-800/40 p-4">
        <h2 className="mb-2 text-lg font-medium text-slate-100">Run pipeline with thermal stage</h2>
        <p className="mb-3 text-sm text-slate-400">
          Run the full pipeline (routing, inverse design, then optional thermal report). The thermal stage produces a report from routing and phase data.
        </p>
        <Link
          to="/run/pipeline"
          className="inline-flex rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-offset-2 focus:ring-offset-slate-900"
        >
          Open Run Pipeline
        </Link>
      </section>

      <section className="rounded-xl border border-slate-700/60 bg-slate-800/40 p-4">
        <h2 className="mb-2 text-lg font-medium text-slate-100">Thermal config schema</h2>
        <p className="mb-3 text-sm text-slate-400">
          View and edit thermal configuration via the config forms (schema: thermal).
        </p>
        <Link
          to="/config"
          className="inline-flex rounded-lg border border-slate-600 bg-slate-700 px-4 py-2 text-sm font-medium text-slate-200 hover:bg-slate-600 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-offset-2 focus:ring-offset-slate-900"
        >
          Open Config forms
        </Link>
        <p className="mt-2 text-xs text-slate-500">
          Select &quot;Thermal config&quot; in the schema dropdown to load the thermal schema.
        </p>
      </section>
    </div>
  )
}
