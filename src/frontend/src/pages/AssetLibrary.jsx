import { Package } from 'lucide-react'

export default function AssetLibrary() {
  return (
    <div className="rounded-xl border border-slate-700/60 bg-slate-800/60 p-8 text-center">
      <Package className="mx-auto h-12 w-12 text-slate-500" />
      <h2 className="mt-3 text-lg font-medium text-slate-200">Asset Library</h2>
      <p className="mt-1 text-sm text-slate-500">
        Saved topologies and meta-atoms will be available here in a future release.
      </p>
    </div>
  )
}
