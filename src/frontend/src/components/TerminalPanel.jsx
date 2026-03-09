import { useState, useEffect, useRef } from 'react'
import { Terminal, ChevronDown, ChevronUp } from 'lucide-react'
import { useWorkspaceCanvas } from '../contexts/WorkspaceCanvasContext'

/**
 * Collapsible bottom panel showing live run log (SSE). Uses log lines and taskId from WorkspaceCanvasContext.
 * When no active run, shows "No active run" or retains last run's lines.
 */
export default function TerminalPanel({ apiBase }) {
  const [collapsed, setCollapsed] = useState(false)
  const canvasContext = useWorkspaceCanvas()
  const bottomRef = useRef(null)

  const taskId = canvasContext?.currentTaskId ?? null
  const logLines = canvasContext?.logLines ?? []

  useEffect(() => {
    if (collapsed) return
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logLines.length, collapsed])

  if (!canvasContext) return null

  return (
    <div className="border-t border-slate-700/60 bg-slate-900/95">
      <button
        type="button"
        onClick={() => setCollapsed((c) => !c)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm font-medium text-slate-300 hover:bg-slate-800/80"
      >
        <Terminal className="h-4 w-4 text-sky-400" />
        <span>Execution log</span>
        {taskId && (
          <span className="rounded bg-sky-500/20 px-1.5 py-0.5 text-xs text-sky-300">Running…</span>
        )}
        {collapsed ? <ChevronDown className="ml-auto h-4 w-4" /> : <ChevronUp className="ml-auto h-4 w-4" />}
      </button>
      {!collapsed && (
        <div className="max-h-48 overflow-y-auto font-mono text-xs text-slate-400 bg-slate-950/80 px-3 py-2">
          {logLines.length === 0 && !taskId && (
            <p className="text-slate-500">No active run. Start a pipeline run from the Canvas to see live logs.</p>
          )}
          {logLines.length === 0 && taskId && (
            <p className="text-slate-500">Connecting to stream…</p>
          )}
          {logLines.map((line, i) => (
            <div key={i} className="whitespace-pre-wrap break-all">
              {line}
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
      )}
    </div>
  )
}
