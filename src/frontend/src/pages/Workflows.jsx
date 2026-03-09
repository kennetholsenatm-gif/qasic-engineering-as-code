import { useCallback, useState, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ReactFlow,
  ReactFlowProvider,
  addEdge,
  useNodesState,
  useEdgesState,
  useReactFlow,
  Background,
  Controls,
  MiniMap,
  MarkerType,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import TaskNode from '../components/TaskNode'
import ConfigDrawer from '../components/ConfigDrawer'
import { Save, Play, CheckCircle, Loader2, GitBranch, Key, FileCode, LayoutTemplate } from 'lucide-react'

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

function fetchCredentialsStatus(apiBase) {
  return fetch(`${apiBase}/api/settings/credentials`).then((r) => {
    if (!r.ok) return { ibm_quantum_token_configured: false, credentials_source: 'vault' }
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

function apiNodesToFlow(nodes, taskTypes = []) {
  return (nodes || []).map((n) => {
    const data = n.data || {}
    const tt = taskTypes.find((t) => t.id === data.task_type)
    return {
      id: n.id,
      type: n.type || 'taskNode',
      data: { ...data, compute_resource: data.compute_resource ?? tt?.compute_resource },
      position: n.position || { x: 0, y: 0 },
    }
  })
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

const DRAG_TYPE = 'application/x-qasic-task-type'

function WorkflowsInner({ apiBase }) {
  const [dagId, setDagId] = useState(null)
  const [dagName, setDagName] = useState('New workflow')
  const [projectId, setProjectId] = useState(null)
  const [validationResult, setValidationResult] = useState(null)
  const [runResult, setRunResult] = useState(null)
  const [selectedNodeId, setSelectedNodeId] = useState(null)
  const [ibmToken, setIbmToken] = useState('')
  const [externalCredsPath, setExternalCredsPath] = useState('')
  const [qasmString, setQasmString] = useState('')
  const [circuitName, setCircuitName] = useState('')
  const [runMode, setRunMode] = useState('dag')
  const circuitFileInputRef = useRef(null)
  const queryClient = useQueryClient()
  const { screenToFlowPosition } = useReactFlow()

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

  const { data: credentialsStatus, refetch: refetchCredentials } = useQuery({
    queryKey: ['credentials-status', apiBase],
    queryFn: () => fetchCredentialsStatus(apiBase),
  })
  const credStatus = credentialsStatus || {}

  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])

  const addNodeAtPosition = useCallback(
    (taskType, position) => {
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
            compute_resource: tt.compute_resource,
          },
          position: position || { x: 250 + (nds.length % 3) * 180, y: 100 + Math.floor(nds.length / 3) * 100 },
        },
      ])
    },
    [taskTypes, setNodes]
  )

  const addNode = useCallback(
    (taskType) => addNodeAtPosition(taskType, null),
    [addNodeAtPosition]
  )

  const onDrop = useCallback(
    (event) => {
      event.preventDefault()
      const raw = event.dataTransfer.getData(DRAG_TYPE)
      if (!raw) return
      try {
        const taskType = JSON.parse(raw)
        const position = screenToFlowPosition({ x: event.clientX, y: event.clientY })
        addNodeAtPosition(taskType, position)
      } catch (_) {
        // ignore invalid drop
      }
    },
    [screenToFlowPosition, addNodeAtPosition]
  )

  const onDragOver = useCallback((event) => {
    event.preventDefault()
    event.dataTransfer.dropEffect = 'move'
  }, [])

  const onConnect = useCallback(
    (params) => setEdges((eds) => addEdge({ ...params, type: 'smoothstep', markerEnd: { type: MarkerType.ArrowClosed } }, eds)),
    [setEdges]
  )

  const selectedNode = nodes.find((n) => n.id === selectedNodeId)
  const selectedTaskType = selectedNode ? taskTypes.find((t) => t.id === selectedNode.data?.task_type) : null
  const supportedBackends = selectedTaskType?.backends || []

  const onNodeClick = useCallback((_ev, node) => setSelectedNodeId(node.id), [])
  const onPaneClick = useCallback(() => setSelectedNodeId(null), [])

  const setSelectedNodeConfig = useCallback(
    (config) => {
      if (!selectedNodeId) return
      setNodes((nds) =>
        nds.map((n) =>
          n.id === selectedNodeId ? { ...n, data: { ...n.data, config } } : n
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
      const baseBody =
        runMode === 'circuit_pipeline' && qasmString.trim()
          ? { qasm_string: qasmString.trim(), circuit_name: circuitName.trim() || 'circuit', run_mode: 'circuit_pipeline' }
          : { run_mode: 'dag' }
      const body = { ...baseBody, project_id: projectId ?? undefined }
      const res = await fetch(`${apiBase}/api/dag/${dagId}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data.detail || res.statusText)
      return data
    },
    onSuccess: (data) => {
      setRunResult(data)
      queryClient.invalidateQueries({ queryKey: ['dag-runs', apiBase, dagId] })
    },
  })

  const saveCredentialsMutation = useMutation({
    mutationFn: async (payload) => {
      const res = await fetch(`${apiBase}/api/settings/credentials`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data.detail || res.statusText)
      return data
    },
    onSuccess: () => {
      refetchCredentials()
    },
  })

  const setCredentialsSourceMutation = useMutation({
    mutationFn: async ({ credentials_source, credentials_path }) => {
      const res = await fetch(`${apiBase}/api/settings/credentials/source`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ credentials_source, credentials_path: credentials_path || '' }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data.detail || res.statusText)
      return data
    },
    onSuccess: () => {
      refetchCredentials()
    },
  })

  function handleSaveCredentials() {
    const payload = {}
    if (ibmToken.trim()) payload.ibm_quantum_token = ibmToken.trim()
    if (Object.keys(payload).length === 0) return
    saveCredentialsMutation.mutate(payload)
  }

  function handleUseExternalFile() {
    const path = externalCredsPath.trim()
    if (!path) return
    setCredentialsSourceMutation.mutate({ credentials_source: 'file', credentials_path: path })
  }

  function handleQasmFileChange(e) {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => {
      if (typeof reader.result === 'string') setQasmString(reader.result)
    }
    reader.readAsText(file)
    if (circuitFileInputRef.current) circuitFileInputRef.current.value = ''
  }

  const { data: runsData } = useQuery({
    queryKey: ['dag-runs', apiBase, dagId],
    queryFn: () => fetch(`${apiBase}/api/dag/${dagId}/runs`).then((r) => (r.ok ? r.json() : { runs: [] })),
    enabled: !!dagId,
  })
  const runs = runsData?.runs || []

  useEffect(() => {
    if (!selectedDag || selectedDag.id !== dagId) return
    if (selectedDag.nodes?.length || selectedDag.edges?.length) {
      setNodes(apiNodesToFlow(selectedDag.nodes, taskTypes))
      setEdges(apiEdgesToFlow(selectedDag.edges))
    }
    if (selectedDag.name) setDagName(selectedDag.name)
  }, [dagId, selectedDag, taskTypes])

  const fixedPipelineTaskIds = ['routing', 'inverse_design', 'heac_phases_to_geometry', 'manifest_to_gds']
  const loadFixedPipelineTemplate = useCallback(() => {
    const templateTypes = fixedPipelineTaskIds
      .map((id) => taskTypes.find((t) => t.id === id))
      .filter(Boolean)
    if (templateTypes.length === 0) return
    const step = 220
    const newNodes = templateTypes.map((tt, i) => {
      const nodeId = `node_fixed_${tt.id}_${Date.now()}_${i}`
      return {
        id: nodeId,
        type: 'taskNode',
        data: {
          label: tt.label,
          task_type: tt.id,
          config: { ...(tt.default_config || {}), backend: tt.default_config?.backend || 'local' },
          compute_resource: tt.compute_resource,
        },
        position: { x: i * step, y: 80 },
      }
    })
    const newEdges = []
    for (let i = 0; i < newNodes.length - 1; i++) {
      newEdges.push({
        id: `e_${newNodes[i].id}_${newNodes[i + 1].id}`,
        source: newNodes[i].id,
        target: newNodes[i + 1].id,
        type: 'smoothstep',
        markerEnd: { type: MarkerType.ArrowClosed },
      })
    }
    setNodes(newNodes)
    setEdges(newEdges)
    setDagName('Fixed metasurface pipeline')
    setSelectedNodeId(null)
  }, [taskTypes, setNodes, setEdges])

  return (
    <div className="flex h-[calc(100vh-8rem)] gap-4">
      <aside className="w-56 shrink-0 rounded-xl border border-slate-700 bg-slate-800/80 p-3 overflow-y-auto">
        <h2 className="text-sm font-semibold text-slate-300 mb-1">Task types</h2>
        <p className="text-xs text-slate-500 mb-3">Drag onto canvas or click to add</p>
        {taskTypes.length === 0 && (
          <p className="text-xs text-slate-500 italic">Loading task types…</p>
        )}
        <ul className="space-y-1">
          {taskTypes.map((tt) => (
            <li key={tt.id}>
              <button
                type="button"
                draggable
                onDragStart={(e) => {
                  e.dataTransfer.setData(DRAG_TYPE, JSON.stringify(tt))
                  e.dataTransfer.effectAllowed = 'move'
                }}
                onClick={() => addNode(tt)}
                className="w-full text-left rounded-lg border border-slate-600 bg-slate-700/50 px-2 py-1.5 text-sm text-slate-200 hover:bg-slate-600 hover:border-slate-500 cursor-grab active:cursor-grabbing"
              >
                {tt.label}
              </button>
            </li>
          ))}
        </ul>
        <div className="mt-4 pt-3 border-t border-slate-700">
          <button
            type="button"
            onClick={loadFixedPipelineTemplate}
            disabled={taskTypes.length === 0}
            className="w-full inline-flex items-center gap-1.5 rounded-lg border border-sky-600/60 bg-sky-500/10 px-2 py-2 text-sm text-sky-300 hover:bg-sky-500/20 disabled:opacity-50"
          >
            <LayoutTemplate className="h-4 w-4" />
            Load fixed pipeline
          </button>
          <p className="text-xs text-slate-500 mt-1">Routing → Inverse → HEaC → GDS</p>
        </div>
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
            disabled={
              runMutation.isPending ||
              !dagId ||
              (runMode === 'circuit_pipeline' && !qasmString.trim())
            }
            title={
              !dagId
                ? 'Save the workflow first, then Run'
                : runMode === 'circuit_pipeline' && !qasmString.trim()
                  ? 'Enter a circuit for circuit-driven pipeline'
                  : 'Deploy and run this DAG'
            }
            className="inline-flex items-center gap-1.5 rounded-lg bg-green-600 px-3 py-1.5 text-sm text-white hover:bg-green-500 disabled:opacity-60"
          >
            {runMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
            Deploy / Run
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

        <div className="flex flex-1 min-h-0 gap-0">
        <div className="flex-1 rounded-xl border border-slate-700 bg-slate-900 min-h-[400px] relative">
          {nodes.length === 0 && (
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <p className="text-sm text-slate-500">Drag task types here or click a type in the palette to add a node.</p>
            </div>
          )}
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
            onDrop={onDrop}
            onDragOver={onDragOver}
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
            <Background variant="dots" gap={12} size={0.5} className="bg-slate-900" />
            <Controls className="!bg-slate-800 !border-slate-600 !rounded-lg" />
            <MiniMap nodeColor="#0f172a" maskColor="rgba(15,23,42,0.8)" className="!bg-slate-800 !rounded-lg" />
          </ReactFlow>
        </div>
        {selectedNode && (
          <div className="w-72 shrink-0 flex flex-col rounded-r-xl border border-slate-700 border-l-0 bg-slate-800/95">
            <ConfigDrawer
              node={selectedNode}
              taskType={selectedTaskType}
              supportedBackends={supportedBackends}
              onConfigChange={setSelectedNodeConfig}
              onClose={() => setSelectedNodeId(null)}
            />
          </div>
        )}
        </div>
      </main>

      <aside className="w-72 shrink-0 rounded-xl border border-slate-700 bg-slate-800/80 p-3 overflow-y-auto space-y-4">
        <section>
          <h2 className="text-sm font-semibold text-slate-300 mb-2 flex items-center gap-1.5">
            <Key className="h-4 w-4 text-sky-400" />
            API credentials
          </h2>
          <p className="text-xs text-slate-500 mb-2">Stored in vault; used when running pipeline (e.g. IBM QPU).</p>
          {credStatus.ibm_quantum_token_configured && (
            <p className="text-xs text-green-400 mb-2">IBM Quantum token configured</p>
          )}
          {credStatus.credentials_source === 'file' && credStatus.credentials_path && (
            <p className="text-xs text-slate-400 mb-2">Using external file</p>
          )}
          <div className="space-y-2">
            <label className="block text-xs text-slate-500">IBM Quantum token</label>
            <input
              type="password"
              value={ibmToken}
              onChange={(e) => setIbmToken(e.target.value)}
              placeholder="Optional"
              className="w-full rounded border border-slate-600 bg-slate-800 text-slate-200 text-sm px-2 py-1.5 placeholder:text-slate-500"
              autoComplete="off"
            />
            <button
              type="button"
              onClick={handleSaveCredentials}
              disabled={saveCredentialsMutation.isPending || !ibmToken.trim()}
              className="w-full inline-flex items-center justify-center gap-1.5 rounded-lg bg-sky-600 px-2 py-1.5 text-sm text-white hover:bg-sky-500 disabled:opacity-60"
            >
              {saveCredentialsMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Save to vault
            </button>
          </div>
          <div className="mt-3 pt-3 border-t border-slate-700">
            <label className="block text-xs text-slate-500 mb-1">Use external file (path)</label>
            <input
              type="text"
              value={externalCredsPath}
              onChange={(e) => setExternalCredsPath(e.target.value)}
              placeholder="/path/to/credentials.json"
              className="w-full rounded border border-slate-600 bg-slate-800 text-slate-200 text-sm px-2 py-1.5 placeholder:text-slate-500 mb-1"
            />
            <div className="flex gap-1">
              <button
                type="button"
                onClick={handleUseExternalFile}
                disabled={setCredentialsSourceMutation.isPending || !externalCredsPath.trim()}
                className="flex-1 rounded-lg border border-slate-600 bg-slate-700 px-2 py-1.5 text-sm text-slate-200 hover:bg-slate-600 disabled:opacity-60"
              >
                Use external file
              </button>
              <button
                type="button"
                onClick={() => setCredentialsSourceMutation.mutate({ credentials_source: 'vault', credentials_path: '' })}
                disabled={setCredentialsSourceMutation.isPending}
                className="rounded-lg border border-slate-600 bg-slate-700 px-2 py-1.5 text-sm text-slate-200 hover:bg-slate-600 disabled:opacity-60"
                title="Use vault (container) again"
              >
                Use vault
              </button>
            </div>
          </div>
        </section>

        <section>
          <h2 className="text-sm font-semibold text-slate-300 mb-2 flex items-center gap-1.5">
            <FileCode className="h-4 w-4 text-sky-400" />
            Circuit (drives pipeline)
          </h2>
          <p className="text-xs text-slate-500 mb-2">OpenQASM to run the full pipeline (qasm→ASIC, routing, inverse, HEaC).</p>
          <div className="space-y-2 mb-2">
            <label className="block text-xs text-slate-500">Run as</label>
            <div className="flex gap-3">
              <label className="flex items-center gap-1.5 text-sm text-slate-300 cursor-pointer">
                <input
                  type="radio"
                  name="runMode"
                  checked={runMode === 'dag'}
                  onChange={() => setRunMode('dag')}
                  className="rounded border-slate-600 text-sky-500"
                />
                DAG (node-by-node)
              </label>
              <label className="flex items-center gap-1.5 text-sm text-slate-300 cursor-pointer">
                <input
                  type="radio"
                  name="runMode"
                  checked={runMode === 'circuit_pipeline'}
                  onChange={() => setRunMode('circuit_pipeline')}
                  className="rounded border-slate-600 text-sky-500"
                />
                Circuit-driven pipeline
              </label>
            </div>
          </div>
          {runMode === 'circuit_pipeline' && (
            <p className="text-xs text-amber-400 mb-2">Circuit required for Run.</p>
          )}
          <textarea
            value={qasmString}
            onChange={(e) => setQasmString(e.target.value)}
            placeholder={'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[3];\n...'}
            rows={6}
            className="w-full rounded border border-slate-600 bg-slate-800 px-2 py-1.5 font-mono text-sm text-slate-100 placeholder:text-slate-500"
          />
          <div className="flex flex-wrap items-center gap-2 mt-2">
            <input
              ref={circuitFileInputRef}
              type="file"
              accept=".qasm,.qasm2"
              onChange={handleQasmFileChange}
              className="hidden"
              id="workflow-qasm-file"
            />
            <label
              htmlFor="workflow-qasm-file"
              className="cursor-pointer rounded border border-slate-600 bg-slate-700 px-2 py-1 text-xs text-slate-200 hover:bg-slate-600"
            >
              Upload .qasm
            </label>
            <input
              type="text"
              value={circuitName}
              onChange={(e) => setCircuitName(e.target.value)}
              placeholder="Circuit name"
              className="w-28 rounded border border-slate-600 bg-slate-800 px-2 py-1 text-sm text-slate-200 placeholder:text-slate-500"
            />
          </div>
        </section>
      </aside>
    </div>
  )
}

export default function Workflows({ apiBase }) {
  return (
    <>
      <h1 className="flex items-center gap-2 text-2xl font-semibold text-slate-100 mb-2">
        <GitBranch className="h-7 w-7 text-sky-400" />
        Flow-based workflow (DAG)
      </h1>
      <p className="text-sm text-slate-500 mb-4">
        Drag task types onto the canvas or click to add. Connect outputs to inputs to form a DAG, then Save, Validate, and Deploy / Run.
      </p>
      <ReactFlowProvider>
        <WorkflowsInner apiBase={apiBase} />
      </ReactFlowProvider>
    </>
  )
}
