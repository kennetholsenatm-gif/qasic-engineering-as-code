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
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import dagre from 'dagre'

const NODE_WIDTH = 80
const NODE_HEIGHT = 36

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
      type: 'default',
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
      <div className={`rounded-lg border border-slate-700 bg-slate-800/60 p-6 text-slate-400 ${className}`}>
        Enter valid OpenQASM to see circuit topology.
      </div>
    )
  }
  if (!isValid) {
    return (
      <div className={`rounded-lg border border-slate-700 bg-slate-800/60 p-6 text-slate-400 ${className}`}>
        Enter valid OpenQASM to see circuit topology.
      </div>
    )
  }
  if (isLoading || isFetching) return <div className={`rounded-lg border border-slate-700 bg-slate-800/60 p-6 ${className}`}>Loading topology…</div>
  if (error) return <div className={`rounded-lg border border-slate-700 bg-slate-800/60 p-6 text-red-400 ${className}`}>{error.message}</div>
  if (!initialNodes.length) {
    return (
      <div className={`rounded-lg border border-slate-700 bg-slate-800/60 p-6 text-slate-400 ${className}`}>
        No qubit interactions (single-qubit gates only).
      </div>
    )
  }

  return (
    <div className={`h-[360px] rounded-lg border border-slate-700 bg-slate-900 overflow-hidden ${className}`}>
      <ReactFlowProvider>
        <ReactFlow
          nodes={nodes.length ? nodes : initialNodes}
          edges={edges.length ? edges : initialEdges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          minZoom={0.2}
          maxZoom={1.5}
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable={false}
          proOptions={{ hideAttribution: true }}
        >
          <Background variant="dots" gap={12} size={0.5} className="bg-slate-900" />
          <Controls className="!bg-slate-800 !border-slate-600 !rounded-lg" />
          <MiniMap nodeColor="#0f172a" maskColor="rgba(15,23,42,0.8)" className="!bg-slate-800 !rounded-lg" />
        </ReactFlow>
      </ReactFlowProvider>
    </div>
  )
}
