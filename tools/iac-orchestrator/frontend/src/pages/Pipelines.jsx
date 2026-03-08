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
import StageNode from '../components/StageNode'
import { Save, Play, Loader2, List } from 'lucide-react'

const nodeTypes = { stageNode: StageNode }

function fetchStageTypes(apiBase) {
  return fetch(`${apiBase}/api/stage-types`).then((r) => {
    if (!r.ok) throw new Error(r.statusText)
    return r.json()
  })
}

function fetchPipelines(apiBase) {
  return fetch(`${apiBase}/api/pipelines`).then((r) => (r.ok ? r.json() : { pipelines: [] }))
}

function fetchPipeline(apiBase, pipelineId) {
  return fetch(`${apiBase}/api/pipelines/${pipelineId}`).then((r) => {
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
    type: n.type || 'stageNode',
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

function PipelinesInner({ apiBase }) {
  const [pipelineId, setPipelineId] = useState(null)
  const [pipelineName, setPipelineName] = useState('New pipeline')
  const [runResult, setRunResult] = useState(null)
  const [selectedRunId, setSelectedRunId] = useState(null)
  const queryClient = useQueryClient()

  const { data: stageTypesData } = useQuery({
    queryKey: ['stage-types', apiBase],
    queryFn: () => fetchStageTypes(apiBase),
  })
  const stageTypes = stageTypesData?.stage_types || []

  const { data: pipelinesData } = useQuery({
    queryKey: ['pipelines', apiBase],
    queryFn: () => fetchPipelines(apiBase),
  })
  const pipelines = pipelinesData?.pipelines || []

  const { data: selectedPipeline, isLoading: loadingPipeline } = useQuery({
    queryKey: ['pipeline', apiBase, pipelineId],
    queryFn: () => fetchPipeline(apiBase, pipelineId),
    enabled: !!pipelineId,
  })

  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])

  const addNode = useCallback(
    (stageType) => {
      const st = stageTypes.find((t) => t.id === stageType.id)
      if (!st) return
      const id = `node_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`
      setNodes((nds) => [
        ...nds,
        {
          id,
          type: 'stageNode',
          data: {
            label: st.label,
            stage_type: st.id,
            config: st.id.startsWith('tofu_') ? { tofu_root: 'infra/tofu' } : {},
          },
          position: { x: 250 + (nds.length % 3) * 180, y: 100 + Math.floor(nds.length / 3) * 100 },
        },
      ])
    },
    [stageTypes, setNodes]
  )

  const onConnect = useCallback(
    (params) =>
      setEdges((eds) =>
        addEdge({ ...params, type: 'smoothstep', markerEnd: { type: MarkerType.ArrowClosed } }, eds)
      ),
    [setEdges]
  )

  const approveMutation = useMutation({
    mutationFn: async ({ runId, nodeId, approved }) => {
      const res = await fetch(`${apiBase}/api/runs/${runId}/approve/${nodeId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approved }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data.detail || res.statusText)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['run', apiBase, selectedRunId] })
      queryClient.invalidateQueries({ queryKey: ['runs', apiBase, pipelineId] })
    },
  })

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (pipelineId) {
        const res = await fetch(`${apiBase}/api/pipelines/${pipelineId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: pipelineName,
            nodes: flowNodesToApi(nodes),
            edges: flowEdgesToApi(edges),
          }),
        })
        const data = await res.json().catch(() => ({}))
        if (!res.ok) throw new Error(data.detail || res.statusText)
        return data
      }
      const res = await fetch(`${apiBase}/api/pipelines`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: pipelineName,
          nodes: flowNodesToApi(nodes),
          edges: flowEdgesToApi(edges),
        }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data.detail || res.statusText)
      return data
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['pipelines', apiBase] })
      if (data.id) setPipelineId(data.id)
    },
  })

  const runMutation = useMutation({
    mutationFn: async () => {
      if (!pipelineId) throw new Error('Save the pipeline first.')
      const res = await fetch(`${apiBase}/api/pipelines/${pipelineId}/run`, { method: 'POST' })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data.detail || res.statusText)
      return data
    },
    onSuccess: (data) => {
      setRunResult(data)
      setSelectedRunId(data.run_id)
      queryClient.invalidateQueries({ queryKey: ['runs', apiBase, pipelineId] })
    },
  })

  const { data: runsData } = useQuery({
    queryKey: ['runs', apiBase, pipelineId],
    queryFn: () =>
      fetch(`${apiBase}/api/pipelines/${pipelineId}/runs`).then((r) => (r.ok ? r.json() : { runs: [] })),
    enabled: !!pipelineId,
  })
  const runs = runsData?.runs || []

  const { data: runDetail } = useQuery({
    queryKey: ['run', apiBase, selectedRunId],
    queryFn: () => fetch(`${apiBase}/api/runs/${selectedRunId}`).then((r) => (r.ok ? r.json() : null)),
    enabled: !!selectedRunId,
    refetchInterval: runs.find((r) => r.id === selectedRunId)?.status === 'running' ? 2000 : false,
  })

  useEffect(() => {
    if (!selectedPipeline || selectedPipeline.id !== pipelineId) return
    if (selectedPipeline.nodes?.length || selectedPipeline.edges?.length) {
      setNodes(apiNodesToFlow(selectedPipeline.nodes))
      setEdges(apiEdgesToFlow(selectedPipeline.edges))
    }
    if (selectedPipeline.name) setPipelineName(selectedPipeline.name)
  }, [pipelineId, selectedPipeline])

  return (
    <div className="flex h-screen flex-col bg-slate-900">
      <header className="flex items-center gap-4 border-b border-slate-700 px-4 py-2">
        <h1 className="text-lg font-semibold text-slate-100">IaC Orchestrator</h1>
        <span className="text-sm text-slate-500">Pipeline DAG → OpenTofu</span>
      </header>
      <div className="flex flex-1 gap-4 overflow-hidden p-4">
        <aside className="w-56 shrink-0 overflow-y-auto rounded-xl border border-slate-700 bg-slate-800/80 p-3">
          <h2 className="mb-2 text-sm font-semibold text-slate-300">Stage types</h2>
          <p className="mb-3 text-xs text-slate-500">Click to add node</p>
          <ul className="space-y-1">
            {stageTypes.map((st) => (
              <li key={st.id}>
                <button
                  type="button"
                  onClick={() => addNode(st)}
                  className="w-full rounded-lg border border-slate-600 bg-slate-700/50 px-2 py-1.5 text-left text-sm text-slate-200 hover:bg-slate-600"
                >
                  {st.label}
                </button>
              </li>
            ))}
          </ul>
          <div className="mt-4">
            <label className="mb-1 block text-xs text-slate-500">Load pipeline</label>
            <select
              value={pipelineId ?? ''}
              onChange={(e) => {
                const id = e.target.value ? Number(e.target.value) : null
                setPipelineId(id)
                if (!id) {
                  setNodes([])
                  setEdges([])
                  setPipelineName('New pipeline')
                }
              }}
              className="w-full rounded border border-slate-600 bg-slate-800 px-2 py-1.5 text-sm text-slate-200"
            >
              <option value="">— New —</option>
              {pipelines.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>
        </aside>

        <main className="flex flex-1 flex-col min-w-0">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <input
              type="text"
              value={pipelineName}
              onChange={(e) => setPipelineName(e.target.value)}
              placeholder="Pipeline name"
              className="w-48 rounded-lg border border-slate-600 bg-slate-800 px-3 py-1.5 text-sm text-slate-100"
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
              onClick={() => runMutation.mutate()}
              disabled={runMutation.isPending || !pipelineId}
              className="inline-flex items-center gap-1.5 rounded-lg bg-green-600 px-3 py-1.5 text-sm text-white hover:bg-green-500 disabled:opacity-60"
            >
              {runMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              Run
            </button>
          </div>

          {runResult && (
            <div className="mb-2 rounded-lg bg-slate-800 px-3 py-2 text-sm text-slate-300">
              Run started: id={runResult.run_id} — {runResult.message}
            </div>
          )}

          <div className="flex flex-1 min-h-0 rounded-xl border border-slate-700 bg-slate-800/50">
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onConnect={onConnect}
              nodeTypes={nodeTypes}
              fitView
              className="rounded-xl"
            >
              <Background />
              <Controls />
              <MiniMap />
            </ReactFlow>
          </div>

          {pipelineId && runs.length > 0 && (
            <div className="mt-4 rounded-lg border border-slate-700 bg-slate-800/80 p-3">
              <h3 className="mb-2 flex items-center gap-1 text-sm font-semibold text-slate-300">
                <List className="h-4 w-4" /> Run history
              </h3>
              <div className="flex flex-wrap gap-2">
                {runs.slice(0, 10).map((r) => (
                  <button
                    key={r.id}
                    type="button"
                    onClick={() => setSelectedRunId(r.id)}
                    className={`rounded px-2 py-1 text-xs ${
                      selectedRunId === r.id
                        ? 'bg-sky-600 text-white'
                        : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                    }`}
                  >
                    #{r.id} {r.status}
                  </button>
                ))}
              </div>
              {runDetail && (
                <div className="mt-3 rounded border border-slate-600 bg-slate-900 p-2 text-xs">
                  <div className="mb-1 font-medium text-slate-400">
                    Run #{runDetail.id} — {runDetail.status} {runDetail.message && `(${runDetail.message})`}
                  </div>
                  {runDetail.stages?.map((s) => (
                    <div key={s.node_id} className="mb-2 border-l-2 border-slate-600 pl-2">
                      <span className="font-medium text-slate-300">{s.node_id}</span>{' '}
                      <span className="text-slate-500">{s.status}</span>
                      {s.status === 'waiting_approval' && (
                        <div className="mt-1 flex gap-2">
                          <button
                            type="button"
                            onClick={() => approveMutation.mutate({ runId: selectedRunId, nodeId: s.node_id, approved: true })}
                            disabled={approveMutation.isPending}
                            className="rounded bg-green-600 px-2 py-0.5 text-xs text-white hover:bg-green-500 disabled:opacity-60"
                          >
                            Approve
                          </button>
                          <button
                            type="button"
                            onClick={() => approveMutation.mutate({ runId: selectedRunId, nodeId: s.node_id, approved: false })}
                            disabled={approveMutation.isPending}
                            className="rounded bg-red-600 px-2 py-0.5 text-xs text-white hover:bg-red-500 disabled:opacity-60"
                          >
                            Reject
                          </button>
                        </div>
                      )}
                      {s.stdout && (
                        <pre className="mt-1 max-h-24 overflow-auto whitespace-pre-wrap text-slate-400">{s.stdout}</pre>
                      )}
                      {s.stderr && (
                        <pre className="mt-1 max-h-24 overflow-auto whitespace-pre-wrap text-red-400">{s.stderr}</pre>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </main>
      </div>
    </div>
  )
}

export default function Pipelines({ apiBase }) {
  return (
    <ReactFlowProvider>
      <PipelinesInner apiBase={apiBase} />
    </ReactFlowProvider>
  )
}
