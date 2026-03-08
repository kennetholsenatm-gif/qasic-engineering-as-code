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

const NODE_WIDTH = 140
const NODE_HEIGHT = 36
const LAYER_GAP = 80
const NODE_GAP = 24

function simpleLayout(nodes, edges) {
  const idToNode = Object.fromEntries(nodes.map((n) => [n.id, { ...n }]))
  const inDegree = {}
  nodes.forEach((n) => { inDegree[n.id] = 0 })
  edges.forEach((e) => { inDegree[e.target] = (inDegree[e.target] || 0) + 1 })
  const layers = []
  const assigned = new Set()
  let current = nodes.filter((n) => inDegree[n.id] === 0).map((n) => n.id)
  while (current.length) {
    layers.push([...current])
    current.forEach((id) => assigned.add(id))
    const next = new Set()
    edges.forEach((e) => {
      if (assigned.has(e.source) && !assigned.has(e.target)) next.add(e.target)
    })
    current = [...next]
  }
  const result = []
  layers.forEach((layer, i) => {
    layer.forEach((id, j) => {
      result.push({
        id,
        data: { label: idToNode[id].label || id },
        position: {
          x: j * (NODE_WIDTH + NODE_GAP),
          y: i * (NODE_HEIGHT + LAYER_GAP),
        },
        type: 'default',
      })
    })
  })
  return result
}

function fetchDag(apiBase) {
  return fetch(`${apiBase}/api/pipeline/dag`).then((r) => {
    if (!r.ok) throw new Error(r.statusText)
    return r.json()
  })
}

export default function PipelineDag({ apiBase, activeStep = null, className = '' }) {
  const { data, error, isLoading } = useQuery({
    queryKey: ['pipeline-dag', apiBase],
    queryFn: () => fetchDag(apiBase),
  })

  const { initialNodes, initialEdges } = useMemo(() => {
    if (!data?.nodes?.length) return { initialNodes: [], initialEdges: [] }
    const nodes = simpleLayout(data.nodes, data.edges || [])
    const edges = (data.edges || []).map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      type: 'smoothstep',
      markerEnd: { type: MarkerType.ArrowClosed },
    }))
    if (activeStep) {
      nodes.forEach((n) => {
        n.data = {
          ...n.data,
          className:
            n.id === activeStep
              ? 'ring-2 ring-green-400 bg-green-900/40'
              : n.type === 'default'
                ? ''
                : '',
        }
      })
    }
    return { initialNodes: nodes, initialEdges: edges }
  }, [data, activeStep])

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)
  useEffect(() => {
    if (initialNodes.length) setNodes(initialNodes)
    if (initialEdges.length) setEdges(initialEdges)
  }, [initialNodes, initialEdges, setNodes, setEdges])

  if (isLoading) return <div className={`rounded-lg border border-slate-700 bg-slate-800/60 p-6 ${className}`}>Loading DAG…</div>
  if (error) return <div className={`rounded-lg border border-slate-700 bg-slate-800/60 p-6 text-red-400 ${className}`}>{error.message}</div>
  if (!initialNodes.length) return null

  return (
    <div className={`h-[360px] rounded-lg border border-slate-700 bg-slate-900 ${className}`}>
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
        nodesDraggable
        nodesConnectable={false}
        elementsSelectable={false}
        proOptions={{ hideAttribution: true }}
      >
        <Background />
        <Controls />
        <MiniMap nodeColor="#0f172a" maskColor="rgba(15,23,42,0.8)" />
      </ReactFlow>
      </ReactFlowProvider>
    </div>
  )
}
