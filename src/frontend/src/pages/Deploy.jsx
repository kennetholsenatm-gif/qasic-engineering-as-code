import { useState } from 'react'
import { Copy, Check, Loader2 } from 'lucide-react'

const TARGETS = [
  { id: 'local', label: 'Local', description: 'Docker Compose or Makefile from repo root' },
  { id: 'vm', label: 'VM', description: 'Deploy to a single VM (script or Tofu)' },
  { id: 'aws', label: 'AWS', description: 'Provision EKS + RDS/ElastiCache, then Helm' },
  { id: 'gcp', label: 'GCP', description: 'Provision GKE, then Helm (coming soon)' },
  { id: 'azure', label: 'Azure', description: 'Provision AKS, then Helm (coming soon)' },
  { id: 'opennebula', label: 'OpenNebula', description: 'OneKE cluster, then Helm (coming soon)' },
]

export default function Deploy({ apiBase }) {
  const [target, setTarget] = useState('local')
  const [awsRegion, setAwsRegion] = useState('us-east-1')
  const [generateResult, setGenerateResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [copied, setCopied] = useState(false)

  const handleGenerate = () => {
    setLoading(true)
    setGenerateResult(null)
    fetch(`${apiBase}/api/deploy/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        target,
        aws_region: target === 'aws' ? awsRegion : undefined,
      }),
    })
      .then(r => r.json())
      .then(d => setGenerateResult(d))
      .catch(e => setGenerateResult({ error: e.message }))
      .finally(() => setLoading(false))
  }

  const commandText = generateResult && !generateResult.error && (
    Array.isArray(generateResult.commands)
      ? generateResult.commands.join('\n\n')
      : generateResult.commands
  )

  const handleCopy = async () => {
    if (!commandText) return
    try {
      await navigator.clipboard.writeText(commandText)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      setGenerateResult((prev) => prev && !prev.error ? { ...prev, copyError: 'Clipboard failed' } : prev)
    }
  }

  return (
    <>
      <h1 className="text-2xl font-semibold text-slate-100">Deploy</h1>
      <p className="text-slate-400 mb-4">
        Choose where to run the QASIC stack. Generate commands to run locally or in your terminal; for full infra DAGs (Tofu init → plan → approval → apply), use the <strong>IaC Orchestrator</strong>.
      </p>

      <section className="mb-6">
        <h2 className="text-lg font-medium text-slate-200 mb-2">Target</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {TARGETS.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setTarget(t.id)}
              className={`rounded-lg border px-4 py-3 text-left transition-colors ${
                target === t.id
                  ? 'border-sky-500 bg-sky-500/10 text-sky-200'
                  : 'border-slate-600 bg-slate-800/60 text-slate-300 hover:border-slate-500 hover:bg-slate-700/40'
              }`}
            >
              <span className="font-medium block">{t.label}</span>
              <span className="text-sm opacity-90">{t.description}</span>
            </button>
          ))}
        </div>
      </section>

      {target === 'aws' && (
        <section className="mb-4">
          <label className="block text-sm font-medium text-slate-300 mb-1">AWS region</label>
          <input
            type="text"
            value={awsRegion}
            onChange={(e) => setAwsRegion(e.target.value)}
            className="rounded bg-slate-800 border border-slate-600 px-3 py-2 text-slate-100 w-48"
            placeholder="us-east-1"
          />
        </section>
      )}

      <section className="mb-4 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={handleGenerate}
          disabled={loading}
          className="inline-flex items-center gap-2 rounded-lg bg-sky-600 px-4 py-2 font-medium text-white hover:bg-sky-500 disabled:opacity-50"
        >
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
          {loading ? 'Generating…' : 'Generate commands'}
        </button>
      </section>

      {generateResult && (
        <section className="mb-6">
          <h2 className="text-lg font-medium text-slate-200 mb-2">Commands</h2>
          {generateResult.error ? (
            <pre className="rounded-lg bg-red-900/20 border border-red-700/50 p-4 text-red-200 text-sm overflow-auto">
              {generateResult.error}
            </pre>
          ) : (
            <>
              {generateResult.hint && (
                <p className="text-slate-400 text-sm mb-2">{generateResult.hint}</p>
              )}
              <div className="relative rounded-lg bg-slate-800 border border-slate-600 overflow-hidden">
                <div className="absolute top-2 right-2 z-10">
                  <button
                    type="button"
                    onClick={handleCopy}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-slate-600 bg-slate-700/90 px-3 py-1.5 text-sm font-medium text-slate-200 hover:bg-slate-600 transition-colors"
                  >
                    {copied ? <Check className="h-4 w-4 text-emerald-400" /> : <Copy className="h-4 w-4" />}
                    {copied ? 'Copied!' : 'Copy'}
                  </button>
                </div>
                <pre className="p-4 pr-24 text-slate-200 text-sm overflow-auto whitespace-pre-wrap max-h-[400px]">
                  {commandText}
                </pre>
              </div>
              {generateResult.copyError && (
                <p className="mt-1 text-sm text-red-400">{generateResult.copyError}</p>
              )}
            </>
          )}
        </section>
      )}

      <section className="border-t border-slate-700 pt-4 text-sm text-slate-400">
        <h2 className="text-lg font-medium text-slate-200 mb-2">Advanced: IaC Orchestrator</h2>
        <p className="mb-2">
          For full control over infrastructure pipelines (Tofu init → plan → approval → apply, custom scripts), run the standalone <strong>IaC Orchestrator</strong> and build your DAG there.
        </p>
        <p>
          From repo root:{' '}
          <code className="rounded bg-slate-800 px-1.5 py-0.5">
            docker compose -f tools/iac-orchestrator/docker-compose.yml up -d --build
          </code>
          , then open <a href="http://localhost:8080" target="_blank" rel="noopener noreferrer" className="text-sky-400 hover:underline">http://localhost:8080</a>.
        </p>
      </section>
    </>
  )
}
