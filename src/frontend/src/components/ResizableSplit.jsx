import { useState, useCallback, useEffect, useRef } from 'react'

/**
 * Simple resizable two-pane layout. Left pane sized by ratio (0–1), right gets the rest.
 */
export default function ResizableSplit({
  left,
  right,
  defaultRatio = 0.6,
  minLeft = 200,
  minRight = 200,
  className = '',
}) {
  const [ratio, setRatio] = useState(defaultRatio)
  const [dragging, setDragging] = useState(false)
  const containerRef = useRef(null)

  const onMouseDown = useCallback(() => setDragging(true), [])
  const onMouseUp = useCallback(() => setDragging(false), [])

  useEffect(() => {
    if (!dragging) return
    const onMove = (e) => {
      const container = containerRef.current
      if (!container) return
      const rect = container.getBoundingClientRect()
      const x = e.clientX - rect.left
      const r = Math.max(0.2, Math.min(0.8, x / rect.width))
      setRatio(r)
    }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onMouseUp)
    return () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onMouseUp)
    }
  }, [dragging, onMouseUp])

  return (
    <div
      ref={containerRef}
      className={`resizable-split-container flex h-full w-full ${className}`}
    >
      <div className="flex shrink-0 overflow-hidden" style={{ width: `${ratio * 100}%`, minWidth: minLeft }}>
        {left}
      </div>
      <div
        role="separator"
        aria-valuenow={ratio}
        onMouseDown={onMouseDown}
        className={`flex w-2 shrink-0 cursor-col-resize items-center justify-center border-x border-slate-600 bg-slate-700/50 hover:bg-sky-500/30 transition-colors ${dragging ? 'bg-sky-500/40' : ''}`}
      >
        <div className="h-12 w-1 rounded-full bg-slate-500" />
      </div>
      <div
        className="flex min-w-0 flex-1 overflow-hidden"
        style={{ minWidth: minRight }}
      >
        {right}
      </div>
    </div>
  )
}
