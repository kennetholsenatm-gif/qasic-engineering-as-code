import { Server } from 'lucide-react'

export default function Compute() {
  return (
    <div className="rounded-xl border border-slate-700/60 bg-slate-800/60 p-8 text-center">
      <Server className="mx-auto h-12 w-12 text-slate-500" />
      <h2 className="mt-3 text-lg font-medium text-slate-200">Compute</h2>
      <p className="mt-1 text-sm text-slate-500">
        Celery / Kubernetes health and queue status will be available here when configured.
      </p>
    </div>
  )
}
