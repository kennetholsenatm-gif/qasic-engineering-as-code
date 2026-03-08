import { useMemo, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
  Handle,
  Position,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import dagre from 'dagre'
import { Check, AlertCircle, Loader2, Clock } from 'lucide-react'

const NODE_WIDTH = 160
const NODE_HEIGHT = 44

const statusConfig = {
  pending: {
    className: 'bg-slate-800/90 backdrop-blur-sm border-slate-500/80 text-slate-300 shadow-md shadow-black/20',
    glow: '',
    Icon: Clock,
    iconClassName: 'text-slate-400',
    handleClass: '!border-slate-400 !bg-slate-600',
    minimapColor: '#475569',
  },
  running: {
    className: 'bg-sky-900/50 backdrop-blur-sm border-sky-400/90 text-slate-100 shadow-lg shadow-sky-500/20 ring-2 ring-sky-500 animate-pulse',
    glow: 'shadow-sky-500/20',
    Icon: Loader2,
    iconClassName: 'text-sky-300 animate-spin',
    handleClass: '!border-sky-400 !bg-sky-500',
    minimapColor: '#0ea5e9',
  },
  success: {
    className: 'bg-emerald-900/40 backdrop-blur-sm border-emerald-500/90 text-slate-100 shadow-lg shadow-emerald-500/20 ring-2 ring-emerald-500/50',
    glow: 'shadow-emerald-500/20',
    Icon: Check,
    iconClassName: 'text-emerald-300',
    handleClass: '!border-emerald-400 !bg-emerald-500',
    minimapColor: '#10b981',
  },
  failed: {
    className: 'bg-red-900/40 backdrop-blur-sm border-red-500/90 text-slate-100 shadow-lg shadow-red-500/20 ring-2 ring-red-500/50',
    glow: 'shadow-red-500/20',
    Icon: AlertCircle,
    iconClassName: 'text-red-300',
    handleClass: '!border-red-400 !bg-red-500',
    minimapColor: '#ef4444',
  },
}

function PipelineNode({ data }) {
  const status = data?.status || 'pending'
  const config = statusConfig[status] || statusConfig.pending
  const Icon = config.Icon

  return (
    <div
      className={`rounded-xl border-2 px-3 py-2 min-w-[160px] min-h-[44px] transition-all duration-200 ease-in-out hover:-translate-y-0.5 hover:border-slate-400 ${config.className}`}
    >
      <Handle
        type="target"
        position={Position.Left}
        className={`!w-3 !h-3 !border-2 !-left-1.5 ${config.handleClass}`}
      />
      <div className="flex items-center gap-2">
        <span className="flex shrink-0" aria-hidden>
          <Icon className={`h-4 w-4 ${config.iconClassName}`} />
        </span>
        <span className="text-sm font-semibold text-slate-100 truncate">{data?.label}</span>
      </div>
      <Handle
        type="source"
        position={Position.Right}
        className={`!w-3 !h-3 !border-2 !-right-1.5 ${config.handleClass}`}
      />
    </div>
  )
}

const nodeTypes = { pipeline: PipelineNode }

function getLayoutedElements(apiNodes, apiEdges, direction = 'LR') {
  const g = new dagre.graphlib.Graph()
  g.setGraph({ rankdir: direction, nodesep: 50, ranksep: 60 })
  g.setDefaultEdgeLabel(() => ({}))
  apiNodes.forEach((n) => g.setNode(n.id, { width: NODE_WIDTH, height: NODE_HEIGHT }))
  ;(apiEdges || []).forEach((e) => g.setEdge(e.source, e.target))
  dagre.layout(g)
  const isHorizontal = direction === 'LR'
  return apiNodes.map((n) => {
    const pos = g.node(n.id)
    return {
      id: n.id,
      data: { label: n.label ?? n.id },
      position: { x: pos.x - NODE_WIDTH / 2, y: pos.y - NODE_HEIGHT / 2 },
      type: 'pipeline',
      sourcePosition: isHorizontal ? 'right' : 'bottom',
      targetPosition: isHorizontal ? 'left' : 'top',
    }
  })
}

function fetchDag(apiBase) {
  return fetch(`${apiBase}/api/pipeline/dag`).then((r) => {
    if (!r.ok) throw new Error(r.statusText)
    return r.json()
  })
}

export default function PipelineDag({ apiBase, activeStep = null, nodeStatuses = {}, className = '' }) {
  const { data, error, isLoading } = useQuery({
    queryKey: ['pipeline-dag', apiBase],
    queryFn: () => fetchDag(apiBase),
  })

  const runningIds = useMemo(
    () => new Set(Object.entries(nodeStatuses).filter(([, v]) => v === 'running').map(([k]) => k)),
    [nodeStatuses]
  )

  const { initialNodes, initialEdges } = useMemo(() => {
    if (!data?.nodes?.length) return { initialNodes: [], initialEdges: [] }
    const nodes = getLayoutedElements(data.nodes, data.edges || [])
    const edges = (data.edges || []).map((e) => {
      const isAdjacentToRunning = runningIds.has(e.source) || runningIds.has(e.target)
      return {
        id: e.id,
        source: e.source,
        target: e.target,
        type: 'smoothstep',
        animated: isAdjacentToRunning,
        style: { strokeWidth: 2, stroke: 'rgb(148, 163, 184)' },
        markerEnd: { type: MarkerType.ArrowClosed },
      }
    })
    nodes.forEach((n) => {
      const status = nodeStatuses[n.id] || (activeStep && n.id === activeStep ? 'running' : 'pending')
      n.data = { ...n.data, status }
    })
    return { initialNodes: nodes, initialEdges: edges }
  }, [data, activeStep, nodeStatuses, runningIds])

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)
  useEffect(() => {
    if (initialNodes.length) setNodes(initialNodes)
    if (initialEdges.length) setEdges(initialEdges)
  }, [initialNodes, initialEdges, setNodes, setEdges])

  const minimapNodeColor = useMemo(() => {
    return (node) => {
      const status = node.data?.status || 'pending'
      return statusConfig[status]?.minimapColor ?? '#475569'
    }
  }, [])

  if (isLoading) {
    return (
      <div className={`rounded-xl border border-slate-700 bg-slate-800/90 backdrop-blur-sm p-6 ${className}`}>
        <span className="text-sm font-medium text-slate-400">Loading DAG…</span>
      </div>
    )
  }
  if (error) {
    return (
      <div className={`rounded-xl border border-slate-700 bg-slate-800/90 backdrop-blur-sm p-6 text-red-400 ${className}`}>
        {error.message}
      </div>
    )
  }
  if (!initialNodes.length) return null

  return (
    <div
      className={`resize-y min-h-[400px] h-[560px] max-h-[800px] rounded-xl border border-slate-700 bg-slate-900 overflow-hidden flex flex-col ${className}`}
      style={{ resize: 'vertical' }}
    >
      <div className="flex-1 min-h-0 relative">
        <ReactFlowProvider>
          <ReactFlow
            nodes={nodes.length ? nodes : initialNodes}
            edges={edges.length ? edges : initialEdges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            nodeTypes={nodeTypes}
            fitView
            fitViewOptions={{ padding: 0.2 }}
            minZoom={0.2}
            maxZoom={1.5}
            nodesDraggable={false}
            nodesConnectable={false}
            elementsSelectable={false}
            proOptions={{ hideAttribution: true }}
          >
            <Background
              variant="dots"
              gap={14}
              size={0.6}
              className="bg-slate-900 [--bg-dot:rgb(51,65,85)]"
            />
            <Controls className="!bg-slate-800/95 !backdrop-blur-sm !border-slate-600 !rounded-xl !shadow-lg !shadow-black/20" />
            <MiniMap
              nodeColor={minimapNodeColor}
              maskColor="rgba(15,23,42,0.85)"
              className="!bg-slate-800/95 !backdrop-blur-sm !rounded-xl !border !border-slate-600"
            />
          </ReactFlow>
        </ReactFlowProvider>
      </div>
      <div
        className="h-2 flex-shrink-0 flex items-center justify-center border-t border-slate-700/80 cursor-ns-resize"
        title="Drag to resize"
        aria-label="Resize workspace"
      >
        <span className="text-slate-500 select-none">⋯</span>
      </div>
    </div>
  )
}
