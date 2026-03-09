import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Box, GitBranch, FileBarChart } from 'lucide-react'
import PhaseViewer3D from '../pages/PhaseViewer3D'
import CircuitTopologyDag from './CircuitTopologyDag'
import { useWorkspaceCanvas } from '../contexts/WorkspaceCanvasContext'

const VIEWS = [
  { id: 'phase', label: 'Phase 3D', icon: Box },
  { id: 'topology', label: 'Circuit topology', icon: GitBranch },
  { id: 'results', label: 'Results', icon: FileBarChart },
]

export default function WorkspaceViewerPane({ apiBase, projectId }) {
  const [view, setView] = useState('phase')
  const canvasContext = useWorkspaceCanvas()
  const isDirty = canvasContext?.isDirty ?? false
  const qasmString = canvasContext?.qasmString ?? ''
  const qasmValid = canvasContext?.qasmValid ?? false

  return (
    <div className="flex h-full flex-col border-l border-slate-700/60 bg-slate-900/80">
      <div className="flex items-center justify-between border-b border-slate-700/60 px-2 py-1.5">
        <div className="flex gap-1">
          {VIEWS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              type="button"
              onClick={() => setView(id)}
              className={`flex items-center gap-1 rounded px-2 py-1 text-xs font-medium transition-colors ${
                view === id ? 'bg-sky-500/20 text-sky-300' : 'text-slate-400 hover:bg-slate-700/60 hover:text-slate-200'
              }`}
            >
              <Icon className="h-3.5 w-3.5" />
              {label}
            </button>
          ))}
        </div>
      </div>
      <div className="relative flex-1 overflow-auto min-h-0">
        {isDirty && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-slate-900/80 backdrop-blur-[2px] rounded-lg">
            <div className="rounded-xl border border-amber-500/50 bg-amber-950/40 px-4 py-3 text-center shadow-lg">
              <p className="text-sm font-medium text-amber-200">Stale</p>
              <p className="mt-0.5 text-xs text-amber-300/90">Re-run pipeline to update the viewer.</p>
            </div>
          </div>
        )}
        <div className="h-full p-2">
          {view === 'phase' && (
            <div className="h-full min-h-[300px] rounded-lg border border-slate-700/60 bg-slate-800/60 overflow-auto">
              <PhaseViewer3D apiBase={apiBase} />
            </div>
          )}
          {view === 'topology' && (
            <div className="h-full min-h-[300px] rounded-lg border border-slate-700/60 bg-slate-800/60 overflow-auto">
              <CircuitTopologyDag
                apiBase={apiBase}
                qasmString={qasmString}
                isValid={qasmValid}
                className="min-h-[280px]"
              />
            </div>
          )}
          {view === 'results' && (
            <div className="flex h-full min-h-[200px] flex-col items-center justify-center gap-2 rounded-lg border border-slate-700/60 bg-slate-800/60 p-4 text-center text-slate-400">
              <FileBarChart className="h-10 w-10 text-slate-500" />
              <p className="text-sm">Latest run stats and outputs</p>
              <Link
                to={projectId ? `/results?project_id=${projectId}` : '/results'}
                className="text-sm text-sky-400 hover:underline"
              >
                View full results →
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
