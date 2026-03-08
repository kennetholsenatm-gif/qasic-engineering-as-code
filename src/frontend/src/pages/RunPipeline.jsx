import { useState, useEffect, useRef, useCallback } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Loader2, Terminal, CheckCircle, AlertCircle } from 'lucide-react'
import { useDropzone } from 'react-dropzone'
import Editor from '@monaco-editor/react'
import PipelineDag from '../components/PipelineDag'
import CircuitTopologyDag from '../components/CircuitTopologyDag'

const POLL_INTERVAL_MS = 2000

function fetchTask(apiBase, taskId) {
  return fetch(`${apiBase}/api/tasks/${taskId}`).then(async (r) => {
    const data = await r.json().catch(() => ({}))
    if (!r.ok) return { status: 'FAILURE', error: data.detail || r.statusText }
    return data
  })
}

function fetchProjects(apiBase) {
  return fetch(`${apiBase}/api/projects`).then(async (r) => {
    if (!r.ok) return { projects: [] }
    const d = await r.json()
    return d
  })
}

export default function RunPipeline({ apiBase }) {
  const [backend, setBackend] = useState('sim')
  const [fast, setFast] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [taskId, setTaskId] = useState(null)
  const [projectId, setProjectId] = useState(null)
  const [logLines, setLogLines] = useState([])
  const logEndRef = useRef(null)
  const eventSourceRef = useRef(null)
  // Circuit ingestion (Phase 1 & 2)
  const [qasmString, setQasmString] = useState('')
  const [circuitName, setCircuitName] = useState('')
  const [fullPipelineWithCircuit, setFullPipelineWithCircuit] = useState(false)
  const fileInputRef = useRef(null)
  const [validationResult, setValidationResult] = useState(null) // { valid, error?, line? }
  const [nodeStatuses, setNodeStatuses] = useState({}) // { [stepId]: 'pending' | 'running' | 'success' | 'failed' }
  const editorRef = useRef(null)
  const monacoRef = useRef(null)
  const validationTimeoutRef = useRef(null)
  const hasSuggestedCircuitDrivenRef = useRef(false)

  const { data: projectsData } = useQuery({
    queryKey: ['projects', apiBase],
    queryFn: () => fetchProjects(apiBase),
    staleTime: 30_000,
  })
  const projects = projectsData?.projects || []

  const submitMutation = useMutation({
    mutationFn: async (body) => {
      const asyncRes = await fetch(`${apiBase}/api/run/pipeline/async`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const asyncData = await asyncRes.json().catch(() => ({}))
      if (asyncRes.ok && asyncData.task_id) return { taskId: asyncData.task_id }
      const syncRes = await fetch(`${apiBase}/api/run/pipeline`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const syncData = await syncRes.json().catch(() => ({}))
      if (!syncRes.ok) throw new Error(syncData.detail || syncRes.statusText)
      return { result: syncData }
    },
    onSuccess: (data) => {
      setError(null)
      if (data.taskId) {
        setTaskId(data.taskId)
        setLogLines([])
      }
      if (data.result) setResult(data.result)
    },
    onError: (err) => setError(err.message),
  })

  const { data: taskData, status: taskStatus } = useQuery({
    queryKey: ['task', apiBase, taskId],
    queryFn: () => fetchTask(apiBase, taskId),
    enabled: !!taskId,
    refetchInterval: (query) => {
      const d = query.state.data
      if (d?.status === 'SUCCESS' || d?.status === 'FAILURE') return false
      return POLL_INTERVAL_MS
    },
    refetchIntervalInBackground: true,
  })

  useEffect(() => {
    if (!taskId || !taskData) return
    if (taskData.status === 'SUCCESS' && taskData.result) {
      if (taskData.result.success === false) {
        setError(taskData.result.error || 'Pipeline failed')
        setResult(null)
      } else {
        setResult(taskData.result)
      }
      setTaskId(null)
    }
    if (taskData.status === 'FAILURE') {
      setError(taskData.error || 'Pipeline failed')
      setTaskId(null)
    }
  }, [taskId, taskData])

  useEffect(() => {
    if (!taskId || !apiBase) return
    setNodeStatuses({})
    const url = `${apiBase.replace(/\/$/, '')}/api/tasks/${taskId}/stream`
    const es = new EventSource(url)
    eventSourceRef.current = es
    es.onmessage = (ev) => {
      try {
        const payload = JSON.parse(ev.data)
        const msg = payload.message || ev.data
        setLogLines((prev) => [...prev, msg])
        const step = payload.step
        const done = !!payload.done
        if (step) {
          setNodeStatuses((prev) => {
            const next = { ...prev }
            const isError = done && typeof msg === 'string' && (msg.toLowerCase().includes('fail') || msg.toLowerCase().includes('error'))
            if (done) {
              next[step] = isError ? 'failed' : 'success'
            } else {
              Object.keys(next).forEach((k) => {
                if (next[k] === 'running') next[k] = 'success'
              })
              next[step] = 'running'
            }
            return next
          })
        }
        if (done) es.close()
      } catch {
        setLogLines((prev) => [...prev, ev.data])
      }
    }
    es.onerror = () => es.close()
    return () => {
      es.close()
      eventSourceRef.current = null
    }
  }, [taskId, apiBase])

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logLines])

  // When QASM becomes non-empty for the first time in session, default circuit-driven to true (once)
  useEffect(() => {
    if (qasmString.trim() && !hasSuggestedCircuitDrivenRef.current) {
      hasSuggestedCircuitDrivenRef.current = true
      setFullPipelineWithCircuit(true)
    }
  }, [qasmString])

  // Debounced live validation (500 ms)
  useEffect(() => {
    if (validationTimeoutRef.current) clearTimeout(validationTimeoutRef.current)
    const s = qasmString.trim()
    if (!s) {
      setValidationResult(null)
      return
    }
    validationTimeoutRef.current = setTimeout(() => {
      fetch(`${apiBase}/api/validate_qasm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ qasm_string: s }),
      })
        .then((r) => r.json())
        .then((data) => setValidationResult(data))
        .catch(() => setValidationResult({ valid: false, error: 'Validation request failed', line: null }))
    }, 500)
    return () => {
      if (validationTimeoutRef.current) clearTimeout(validationTimeoutRef.current)
    }
  }, [qasmString, apiBase])

  const decorationIdsRef = useRef([])
  // Monaco decorations for error line
  useEffect(() => {
    const editor = editorRef.current
    const monaco = monacoRef.current
    if (decorationIdsRef.current.length) {
      editor?.deltaDecorations(decorationIdsRef.current, [])
      decorationIdsRef.current = []
    }
    if (!editor || !monaco || !validationResult || validationResult.valid !== false || validationResult.line == null) return
    const line = Math.max(1, Math.min(validationResult.line, editor.getModel()?.getLineCount() ?? 1))
    const deco = [
      {
        range: new monaco.Range(line, 1, line, 1),
        options: { isWholeLine: true, className: 'qasm-error-line', glyphMarginClassName: 'qasm-error-margin' },
      },
    ]
    decorationIdsRef.current = editor.deltaDecorations([], deco)
    return () => {
      if (editorRef.current && decorationIdsRef.current.length) {
        editorRef.current.deltaDecorations(decorationIdsRef.current, [])
        decorationIdsRef.current = []
      }
    }
  }, [validationResult])

  const onEditorMount = useCallback((editor, monaco) => {
    editorRef.current = editor
    monacoRef.current = monaco
    monaco.languages.register({ id: 'openqasm' })
    monaco.languages.setMonarchTokensProvider('openqasm', {
      keywords: ['OPENQASM', 'include', 'qreg', 'creg', 'barrier', 'gate', 'opaque', 'if', 'reset'],
      gates: ['h', 'x', 'y', 'z', 's', 't', 'sdg', 'tdg', 'cx', 'cnot', 'rx', 'ry', 'rz', 'cz', 'swap', 'id', 'u1', 'u2', 'u3'],
      tokenizer: {
        root: [
          [/\/\/.*$/, 'comment'],
          [/\b(OPENQASM|include|qreg|creg|barrier|gate|opaque|if|reset)\b/, 'keyword'],
          [/\b(h|x|y|z|s|t|cx|cnot|rx|ry|rz|swap|id|u1|u2|u3)\b/i, 'keyword.control'],
          [/q\[\d+\]/, 'string'],
          [/[a-zA-Z_]\w*/, 'identifier'],
          [/\d+\.?\d*/, 'number'],
        ],
      },
    })
    monaco.editor.setModelLanguage(editor.getModel(), 'openqasm')
  }, [])

  const dropzone = useDropzone({
    accept: { 'text/plain': ['.qasm', '.qasm2'], 'application/octet-stream': ['.qasm', '.qasm2'] },
    maxFiles: 1,
    onDropAccepted: (files) => {
      const f = files[0]
      if (f) {
        const reader = new FileReader()
        reader.onload = () => { if (typeof reader.result === 'string') setQasmString(reader.result) }
        reader.readAsText(f)
      }
    },
    noClick: true,
    noKeyboard: true,
  })

  const loading = submitMutation.isPending || (!!taskId && taskStatus !== 'error')
  const statusLabel = taskId
    ? taskData?.status === 'PENDING'
      ? 'In queue'
      : taskData?.status === 'STARTED'
        ? 'Running…'
        : 'Polling…'
    : 'Running…'

  function handleSubmit(e) {
    e.preventDefault()
    setResult(null)
    setError(null)
    setTaskId(null)
    const body = qasmString.trim()
      ? {
          qasm_string: qasmString.trim(),
          circuit_name: circuitName.trim() || undefined,
          full_pipeline_with_circuit: fullPipelineWithCircuit,
          backend,
          fast,
          project_id: projectId || undefined,
        }
      : {
          backend,
          fast,
          project_id: projectId || undefined,
        }
    submitMutation.mutate(body)
  }

  function handleQasmFileChange(e) {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => {
      if (typeof reader.result === 'string') setQasmString(reader.result)
    }
    reader.readAsText(file)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const activeStep = taskData?.status === 'STARTED' ? 'routing' : null
  const [dagTab, setDagTab] = useState('pipeline') // 'pipeline' | 'topology'
  const isQasmValid = validationResult?.valid === true

  return (
    <>
      <h1 className="text-2xl font-semibold text-slate-100">Run full pipeline</h1>
      <p className="mt-1 text-sm text-slate-500">
        Pipeline runs on a Celery worker when available (routing + inverse); otherwise runs in the API.
      </p>

      <section className="mt-6">
        <div className="mb-2 flex items-center gap-2">
          <h2 className="text-sm font-medium text-slate-400">DAG</h2>
          <div className="flex rounded-lg border border-slate-600 bg-slate-800/60 p-0.5">
            <button
              type="button"
              onClick={() => setDagTab('pipeline')}
              className={`rounded-md px-3 py-1 text-sm ${dagTab === 'pipeline' ? 'bg-slate-600 text-slate-100' : 'text-slate-400 hover:text-slate-200'}`}
            >
              Pipeline (DevOps)
            </button>
            <button
              type="button"
              onClick={() => setDagTab('topology')}
              className={`rounded-md px-3 py-1 text-sm ${dagTab === 'topology' ? 'bg-slate-600 text-slate-100' : 'text-slate-400 hover:text-slate-200'}`}
            >
              Circuit Topology (EaC)
            </button>
          </div>
        </div>
        {dagTab === 'pipeline' && <PipelineDag apiBase={apiBase} activeStep={activeStep} nodeStatuses={nodeStatuses} />}
        {dagTab === 'topology' && (
          <CircuitTopologyDag apiBase={apiBase} qasmString={qasmString} isValid={isQasmValid} />
        )}
      </section>

      <section className="mt-6">
        <h2 className="mb-2 text-sm font-medium text-slate-400">Quantum circuit (optional)</h2>
        <p className="mb-2 text-xs text-slate-500">
          Paste OpenQASM 2 or drop a .qasm file to run the Algorithm-to-ASIC pipeline. Leave empty to run the default pipeline only.
        </p>
        <div className="space-y-2">
          <div
            {...dropzone.getRootProps()}
            className={`min-h-[200px] rounded-lg border bg-slate-800 overflow-hidden ${dropzone.isDragActive ? 'border-sky-500 ring-1 ring-sky-500' : 'border-slate-600'}`}
          >
            <input {...dropzone.getInputProps()} />
            <Editor
              height="200px"
              defaultLanguage="openqasm"
              value={qasmString}
              onChange={(v) => setQasmString(v ?? '')}
              onMount={onEditorMount}
              theme="vs-dark"
              options={{
                minimap: { enabled: false },
                fontSize: 13,
                lineNumbers: 'on',
                scrollBeyondLastLine: false,
                wordWrap: 'on',
                padding: { top: 8 },
              }}
              loading={null}
            />
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="rounded-lg border border-slate-600 bg-slate-700 px-3 py-1.5 text-sm text-slate-200 hover:bg-slate-600"
            >
              Upload .qasm file
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".qasm,.qasm2"
              onChange={handleQasmFileChange}
              className="hidden"
            />
            <label htmlFor="circuit-name" className="text-sm text-slate-400">
              Circuit name
            </label>
            {validationResult && (
              <span className="flex items-center gap-1.5 text-sm">
                {validationResult.valid ? (
                  <><CheckCircle className="h-4 w-4 text-emerald-500" aria-hidden /> Valid</>
                ) : (
                  <><AlertCircle className="h-4 w-4 text-red-400" aria-hidden /> Invalid</>
                )}
              </span>
            )}
            <input
              id="circuit-name"
              type="text"
              value={circuitName}
              onChange={(e) => setCircuitName(e.target.value)}
              placeholder="circuit"
              className="w-40 rounded-lg border border-slate-600 bg-slate-800 px-3 py-1.5 text-sm text-slate-100 placeholder:text-slate-500 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
            />
          </div>
          {validationResult && !validationResult.valid && validationResult.error && (
            <p className="text-sm text-red-400" role="alert">
              {validationResult.error}
              {validationResult.line != null && ` (line ${validationResult.line})`}
            </p>
          )}
        </div>
      </section>

      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        {qasmString.trim() && (
          <div className="rounded-xl border border-sky-500/50 bg-sky-950/30 px-4 py-3">
            <div className="flex flex-wrap items-center gap-3">
              <input
                type="checkbox"
                id="full-pipeline-circuit"
                checked={fullPipelineWithCircuit}
                onChange={(e) => setFullPipelineWithCircuit(e.target.checked)}
                className="h-4 w-4 rounded border-slate-600 bg-slate-800 text-sky-500 focus:ring-sky-500"
              />
              <label htmlFor="full-pipeline-circuit" className="text-sm font-medium text-slate-200">
                Circuit-driven pipeline
              </label>
            </div>
            <p className="mt-1.5 text-xs text-slate-400">
              Your circuit drives the full pipeline (qasm → ASIC → routing → inverse → HEaC). Uncheck to run circuit-to-ASIC only.
            </p>
          </div>
        )}
        {projects.length > 0 && (
          <div>
            <label htmlFor="project" className="mb-1.5 block text-sm font-medium text-slate-300">
              Project (optional)
            </label>
            <select
              id="project"
              value={projectId ?? ''}
              onChange={(e) => setProjectId(e.target.value ? Number(e.target.value) : null)}
              className="w-full max-w-xs rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-slate-100 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
            >
              <option value="">— None —</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>
        )}
        <div>
          <label htmlFor="backend" className="mb-1.5 block text-sm font-medium text-slate-300">
            Backend
          </label>
          <select
            id="backend"
            value={backend}
            onChange={(e) => setBackend(e.target.value)}
            className="w-full max-w-xs rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-slate-100 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500 disabled:opacity-60"
          >
            <option value="sim">Simulation</option>
            <option value="hardware">IBM hardware</option>
          </select>
        </div>
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="fast"
            checked={fast}
            onChange={(e) => setFast(e.target.checked)}
            className="h-4 w-4 rounded border-slate-600 bg-slate-800 text-sky-500 focus:ring-sky-500"
          />
          <label htmlFor="fast" className="text-sm text-slate-300">
            Fast
          </label>
        </div>
        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-offset-2 focus:ring-offset-slate-900 disabled:opacity-60 disabled:hover:bg-sky-600"
          >
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                {statusLabel}
              </>
            ) : (
              'Run pipeline'
            )}
          </button>
        </div>
      </form>

      {taskId && (logLines.length > 0 || !taskData?.result) && (
        <div className="mt-4 rounded-xl border border-slate-700 bg-slate-900/80 overflow-hidden">
          <div className="flex items-center gap-2 border-b border-slate-700 bg-slate-800/60 px-3 py-2 text-sm text-slate-400">
            <Terminal className="h-4 w-4" />
            Live log (task: {taskId})
          </div>
          <div className="max-h-48 overflow-y-auto p-3 font-mono text-xs text-slate-300 whitespace-pre-wrap">
            {logLines.length ? logLines.map((line, i) => <div key={i}>{line}</div>) : 'Waiting for output…'}
            <div ref={logEndRef} />
          </div>
        </div>
      )}

      {taskId && !result && !error && logLines.length === 0 && (
        <div className="mt-4 flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800/60 px-4 py-3 text-sm text-slate-400">
          <Loader2 className="h-4 w-4 animate-spin shrink-0" />
          <span>Task ID: {taskId} — {statusLabel}</span>
        </div>
      )}
      {error && <p className="mt-4 text-sm text-red-400">{error}</p>}
      {result && (
        <section className="mt-6 rounded-xl border border-slate-700/60 bg-slate-800/60 p-4">
          <h2 className="text-lg font-medium text-slate-100">Result</h2>
          <pre className="mt-2 overflow-auto rounded-lg bg-slate-900/80 p-4 text-sm text-slate-300">
            {JSON.stringify(result, null, 2)}
          </pre>
        </section>
      )}
    </>
  )
}
