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

const NODE_WIDTH = 88
const NODE_HEIGHT = 40

function TopologyNode({ data }) {
  return (
    <div className="rounded-xl border-2 border-slate-500/80 px-3 py-2 min-w-[88px] min-h-[40px] bg-slate-800/90 backdrop-blur-sm text-slate-100 shadow-md shadow-black/20 transition-all duration-200 ease-in-out hover:-translate-y-0.5 hover:border-slate-400">
      <Handle
        type="target"
        position={Position.Left}
        className="!w-3 !h-3 !border-2 !-left-1.5 !border-slate-400 !bg-slate-600"
      />
      <span className="text-sm font-semibold text-slate-100">{data?.label ?? data?.id}</span>
      <Handle
        type="source"
        position={Position.Right}
        className="!w-3 !h-3 !border-2 !-right-1.5 !border-slate-400 !bg-slate-600"
      />
    </div>
  )
}

const nodeTypes = { topology: TopologyNode }

function getLayoutedElements(apiNodes, apiEdges, direction = 'LR') {
  const g = new dagre.graphlib.Graph()
  g.setGraph({ rankdir: direction, nodesep: 40, ranksep: 50 })
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
      type: 'topology',
      sourcePosition: isHorizontal ? 'right' : 'bottom',
      targetPosition: isHorizontal ? 'left' : 'top',
    }
  })
}

function fetchTopology(apiBase, qasmString) {
  return fetch(`${apiBase}/api/circuit/topology`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ qasm_string: qasmString }),
  }).then((r) => {
    if (!r.ok) return r.json().then((d) => Promise.reject(new Error(d.detail || r.statusText)))
    return r.json()
  })
}

export default function CircuitTopologyDag({ apiBase, qasmString, isValid = false, className = '' }) {
  const trimmed = (qasmString || '').trim()
  const { data, error, isLoading, isFetching } = useQuery({
    queryKey: ['circuit-topology', apiBase, trimmed],
    queryFn: () => fetchTopology(apiBase, trimmed),
    enabled: !!trimmed && !!isValid,
  })

  const { initialNodes, initialEdges } = useMemo(() => {
    if (!data?.nodes?.length) return { initialNodes: [], initialEdges: [] }
    const nodes = getLayoutedElements(data.nodes, data.edges || [])
    const edges = (data.edges || []).map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      type: 'smoothstep',
      style: { strokeWidth: 2, stroke: 'rgb(148, 163, 184)' },
      markerEnd: { type: MarkerType.ArrowClosed },
    }))
    return { initialNodes: nodes, initialEdges: edges }
  }, [data])

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)
  useEffect(() => {
    if (initialNodes.length) setNodes(initialNodes)
    if (initialEdges.length) setEdges(initialEdges)
  }, [initialNodes, initialEdges, setNodes, setEdges])

  if (!trimmed) {
    return (
      <div className={`rounded-xl border border-slate-700 bg-slate-800/90 backdrop-blur-sm p-6 text-slate-400 ${className}`}>
        Enter valid OpenQASM to see circuit topology.
      </div>
    )
  }
  if (!isValid) {
    return (
      <div className={`rounded-xl border border-slate-700 bg-slate-800/90 backdrop-blur-sm p-6 text-slate-400 ${className}`}>
        Enter valid OpenQASM to see circuit topology.
      </div>
    )
  }
  if (isLoading || isFetching) {
    return (
      <div className={`rounded-xl border border-slate-700 bg-slate-800/90 backdrop-blur-sm p-6 ${className}`}>
        <span className="text-sm font-medium text-slate-400">Loading topology…</span>
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
  if (!initialNodes.length) {
    return (
      <div className={`rounded-xl border border-slate-700 bg-slate-800/90 backdrop-blur-sm p-6 text-slate-400 ${className}`}>
        No qubit interactions (single-qubit gates only).
      </div>
    )
  }

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
              nodeColor="#475569"
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
