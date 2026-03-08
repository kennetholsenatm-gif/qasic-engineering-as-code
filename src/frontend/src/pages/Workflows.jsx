import { useCallback, useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ReactFlow,
  ReactFlowProvider,
  addEdge,
  useNodesState,
  useEdgesState,
  Background,
  Controls,
  MiniMap,
  MarkerType,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import TaskNode from '../components/TaskNode'
import { Save, Play, CheckCircle, Loader2, GitBranch } from 'lucide-react'

const nodeTypes = { taskNode: TaskNode }

function fetchTaskTypes(apiBase) {
  return fetch(`${apiBase}/api/dag/task-types`).then((r) => {
    if (!r.ok) throw new Error(r.statusText)
    return r.json()
  })
}

function fetchDags(apiBase, projectId) {
  const url = projectId != null ? `${apiBase}/api/dag?project_id=${projectId}` : `${apiBase}/api/dag`
  return fetch(url).then((r) => (!r.ok ? { dags: [] } : r.json()))
}

function fetchDag(apiBase, dagId) {
  return fetch(`${apiBase}/api/dag/${dagId}`).then((r) => {
    if (!r.ok) throw new Error(r.statusText)
    return r.json()
  })
}

function flowNodesToApi(nodes) {
  return nodes.map((n) => ({
    id: n.id,
    type: n.type,
    data: n.data,
    position: n.position,
  }))
}

function flowEdgesToApi(edges) {
  return edges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    sourceHandle: e.sourceHandle,
    targetHandle: e.targetHandle,
  }))
}

function apiNodesToFlow(nodes) {
  return (nodes || []).map((n) => ({
    id: n.id,
    type: n.type || 'taskNode',
    data: n.data || {},
    position: n.position || { x: 0, y: 0 },
  }))
}

function apiEdgesToFlow(edges) {
  return (edges || []).map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    sourceHandle: e.sourceHandle,
    targetHandle: e.targetHandle,
    type: 'smoothstep',
    markerEnd: { type: MarkerType.ArrowClosed },
  }))
}

function WorkflowsInner({ apiBase }) {
  const [dagId, setDagId] = useState(null)
  const [dagName, setDagName] = useState('New workflow')
  const [projectId, setProjectId] = useState(null)
  const [validationResult, setValidationResult] = useState(null)
  const [runResult, setRunResult] = useState(null)
  const [selectedNodeId, setSelectedNodeId] = useState(null)
  const queryClient = useQueryClient()

  const { data: taskTypesData } = useQuery({
    queryKey: ['dag-task-types', apiBase],
    queryFn: () => fetchTaskTypes(apiBase),
  })
  const taskTypes = taskTypesData?.task_types || []

  const { data: dagsData } = useQuery({
    queryKey: ['dags', apiBase, projectId],
    queryFn: () => fetchDags(apiBase, projectId),
  })
  const dags = dagsData?.dags || []

  const { data: selectedDag, isLoading: loadingDag } = useQuery({
    queryKey: ['dag', apiBase, dagId],
    queryFn: () => fetchDag(apiBase, dagId),
    enabled: !!dagId,
  })

  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])

  const addNode = useCallback(
    (taskType) => {
      const tt = taskTypes.find((t) => t.id === taskType.id)
      if (!tt) return
      const id = `node_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`
      setNodes((nds) => [
        ...nds,
        {
          id,
          type: 'taskNode',
          data: {
            label: tt.label,
            task_type: tt.id,
            config: { ...(tt.default_config || {}), backend: tt.default_config?.backend || 'local' },
          },
          position: { x: 250 + (nds.length % 3) * 180, y: 100 + Math.floor(nds.length / 3) * 100 },
        },
      ])
    },
    [taskTypes, setNodes]
  )

  const onConnect = useCallback(
    (params) => setEdges((eds) => addEdge({ ...params, type: 'smoothstep', markerEnd: { type: MarkerType.ArrowClosed } }, eds)),
    [setEdges]
  )

  const selectedNode = nodes.find((n) => n.id === selectedNodeId)
  const selectedTaskType = selectedNode ? taskTypes.find((t) => t.id === selectedNode.data?.task_type) : null
  const supportedBackends = selectedTaskType?.backends || []

  const onNodeClick = useCallback((_ev, node) => setSelectedNodeId(node.id), [])
  const onPaneClick = useCallback(() => setSelectedNodeId(null), [])

  const setSelectedNodeBackend = useCallback(
    (backend) => {
      if (!selectedNodeId) return
      setNodes((nds) =>
        nds.map((n) =>
          n.id === selectedNodeId
            ? { ...n, data: { ...n.data, config: { ...(n.data?.config || {}), backend } } }
            : n
        )
      )
    },
    [selectedNodeId, setNodes]
  )

  const validateMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch(`${apiBase}/api/dag/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nodes: flowNodesToApi(nodes), edges: flowEdgesToApi(edges) }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data.detail || res.statusText)
      return data
    },
    onSuccess: (data) => setValidationResult(data),
  })

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (dagId) {
        const res = await fetch(`${apiBase}/api/dag/${dagId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: dagName, nodes: flowNodesToApi(nodes), edges: flowEdgesToApi(edges) }),
        })
        const data = await res.json().catch(() => ({}))
        if (!res.ok) throw new Error(data.detail || res.statusText)
        return data
      }
      const res = await fetch(`${apiBase}/api/dag`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: dagName, project_id: projectId || undefined, nodes: flowNodesToApi(nodes), edges: flowEdgesToApi(edges) }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data.detail || res.statusText)
      return data
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['dags', apiBase, projectId] })
      if (data.id) setDagId(data.id)
    },
  })

  const runMutation = useMutation({
    mutationFn: async () => {
      if (!dagId) throw new Error('Save the workflow first.')
      const res = await fetch(`${apiBase}/api/dag/${dagId}/run`, { method: 'POST' })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data.detail || res.statusText)
      return data
    },
    onSuccess: (data) => {
      setRunResult(data)
      queryClient.invalidateQueries({ queryKey: ['dag-runs', apiBase, dagId] })
    },
  })

  const { data: runsData } = useQuery({
    queryKey: ['dag-runs', apiBase, dagId],
    queryFn: () => fetch(`${apiBase}/api/dag/${dagId}/runs`).then((r) => (r.ok ? r.json() : { runs: [] })),
    enabled: !!dagId,
  })
  const runs = runsData?.runs || []

  useEffect(() => {
    if (!selectedDag || selectedDag.id !== dagId) return
    if (selectedDag.nodes?.length || selectedDag.edges?.length) {
      setNodes(apiNodesToFlow(selectedDag.nodes))
      setEdges(apiEdgesToFlow(selectedDag.edges))
    }
    if (selectedDag.name) setDagName(selectedDag.name)
  }, [dagId, selectedDag])

  return (
    <div className="flex h-[calc(100vh-8rem)] gap-4">
      <aside className="w-56 shrink-0 rounded-xl border border-slate-700 bg-slate-800/80 p-3 overflow-y-auto">
        <h2 className="text-sm font-semibold text-slate-300 mb-2">Task types</h2>
        <p className="text-xs text-slate-500 mb-3">Click to add node</p>
        <ul className="space-y-1">
          {taskTypes.map((tt) => (
            <li key={tt.id}>
              <button
                type="button"
                onClick={() => addNode(tt)}
                className="w-full text-left rounded-lg border border-slate-600 bg-slate-700/50 px-2 py-1.5 text-sm text-slate-200 hover:bg-slate-600"
              >
                {tt.label}
              </button>
            </li>
          ))}
        </ul>
        <div className="mt-4">
          <label className="block text-xs text-slate-500 mb-1">Load DAG</label>
          <select
            value={dagId ?? ''}
            onChange={(e) => {
              const id = e.target.value ? Number(e.target.value) : null
              setDagId(id)
              if (!id) {
                setNodes([])
                setEdges([])
                setDagName('New workflow')
              }
            }}
            className="w-full rounded border border-slate-600 bg-slate-800 text-slate-200 text-sm px-2 py-1.5"
          >
            <option value="">— New —</option>
            {dags.map((d) => (
              <option key={d.id} value={d.id}>{d.name}</option>
            ))}
          </select>
        </div>
      </aside>

      <main className="flex-1 flex flex-col min-w-0">
        <div className="flex flex-wrap items-center gap-2 mb-2">
          <input
            type="text"
            value={dagName}
            onChange={(e) => setDagName(e.target.value)}
            placeholder="Workflow name"
            className="rounded-lg border border-slate-600 bg-slate-800 px-3 py-1.5 text-sm text-slate-100 w-48"
          />
          <button
            type="button"
            onClick={() => saveMutation.mutate()}
            disabled={saveMutation.isPending}
            className="inline-flex items-center gap-1.5 rounded-lg bg-sky-600 px-3 py-1.5 text-sm text-white hover:bg-sky-500 disabled:opacity-60"
          >
            {saveMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            Save
          </button>
          <button
            type="button"
            onClick={() => validateMutation.mutate()}
            disabled={validateMutation.isPending}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-600 bg-slate-700 px-3 py-1.5 text-sm text-slate-200 hover:bg-slate-600"
          >
            {validateMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle className="h-4 w-4" />}
            Validate
          </button>
          <button
            type="button"
            onClick={() => runMutation.mutate()}
            disabled={runMutation.isPending || !dagId}
            className="inline-flex items-center gap-1.5 rounded-lg bg-green-600 px-3 py-1.5 text-sm text-white hover:bg-green-500 disabled:opacity-60"
          >
            {runMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
            Run
          </button>
        </div>

        {validationResult && (
          <div className={`mb-2 rounded-lg px-3 py-2 text-sm ${validationResult.valid ? 'bg-green-900/30 text-green-300' : 'bg-red-900/30 text-red-300'}`}>
            {validationResult.valid ? 'DAG is valid.' : validationResult.errors?.map((e, i) => <div key={i}>{e.node_id || 'Graph'}: {e.message}</div>)}
          </div>
        )}
        {runResult && (
          <div className="mb-2 rounded-lg bg-slate-800 px-3 py-2 text-sm text-slate-300">
            Run created: id={runResult.run_id} — {runResult.message}
            {runResult.task_id && ` (task: ${runResult.task_id})`}
          </div>
        )}

        {dagId && runs.length > 0 && (
          <details className="mb-2 rounded-lg border border-slate-700 bg-slate-800/60">
            <summary className="cursor-pointer px-3 py-2 text-sm text-slate-300">Run history</summary>
            <ul className="border-t border-slate-700 px-3 py-2 text-sm">
              {runs.slice(0, 10).map((r) => (
                <li key={r.id} className="flex items-center gap-2 py-1">
                  <span className="text-slate-500">Run {r.id}</span>
                  <span className={r.status === 'success' ? 'text-green-400' : r.status === 'failed' ? 'text-red-400' : 'text-slate-400'}>{r.status}</span>
                  <a href={`${apiBase}/api/dag/runs/${r.id}`} target="_blank" rel="noreferrer" className="text-sky-400 hover:underline">View</a>
                </li>
              ))}
            </ul>
          </details>
        )}

        {selectedNode && (
          <div className="mb-2 rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 flex items-center gap-4">
            <span className="text-sm text-slate-400">Node: {selectedNode.data?.label}</span>
            <label className="text-sm text-slate-400 flex items-center gap-2">
              Backend
              <select
                value={selectedNode.data?.config?.backend || 'local'}
                onChange={(e) => setSelectedNodeBackend(e.target.value)}
                className="rounded border border-slate-600 bg-slate-700 text-slate-200 text-sm px-2 py-1"
              >
                {supportedBackends.map((b) => (
                  <option key={b} value={b}>{b === 'aws_eks' ? 'EKS (cloud)' : b === 'ibm_qpu' ? 'IBM QPU' : 'Local'}</option>
                ))}
              </select>
            </label>
          </div>
        )}

        <div className="flex-1 rounded-xl border border-slate-700 bg-slate-900 min-h-[400px]">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
            nodeTypes={nodeTypes}
            fitView
            fitViewOptions={{ padding: 0.2 }}
            minZoom={0.2}
            maxZoom={1.5}
            nodesDraggable
            nodesConnectable
            elementsSelectable
            connectOnClick={false}
            proOptions={{ hideAttribution: true }}
          >
            <Background />
            <Controls />
            <MiniMap nodeColor="#0f172a" maskColor="rgba(15,23,42,0.8)" />
          </ReactFlow>
        </div>
      </main>
    </div>
  )
}

export default function Workflows({ apiBase }) {
  return (
    <>
      <h1 className="flex items-center gap-2 text-2xl font-semibold text-slate-100 mb-2">
        <GitBranch className="h-7 w-7 text-sky-400" />
        Workflows (DAG)
      </h1>
      <p className="text-sm text-slate-500 mb-4">
        Build a workflow: add nodes from the palette, connect outputs to inputs, then Save, Validate, and Run.
      </p>
      <ReactFlowProvider>
        <WorkflowsInner apiBase={apiBase} />
      </ReactFlowProvider>
    </>
  )
}
