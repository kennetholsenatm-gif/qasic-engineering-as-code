import { useCallback, useState, useEffect } from 'react'
import { X } from 'lucide-react'

/**
 * Right-hand config drawer for a selected DAG node.
 * Renders form fields from task type default_config (backend, routing_method, fast, etc.)
 * and calls onConfigChange when any value changes.
 */
function fieldLabel(key) {
  const labels = {
    backend: 'Backend',
    routing_method: 'Routing method',
    fast: 'Fast mode',
    model: 'Model',
    device: 'Device',
    protocol: 'Protocol',
    n_bits: 'n_bits',
    n_trials: 'n_trials',
    eta: 'η',
    n_b: 'n_b',
    r: 'r',
  }
  return labels[key] || key.replace(/_/g, ' ')
}

function ConfigDrawer({ node, taskType, supportedBackends, onConfigChange, onClose }) {
  const defaultConfig = taskType?.default_config || {}

  const [localConfig, setLocalConfig] = useState(() => ({
    ...defaultConfig,
    ...(node?.data?.config || {}),
  }))

  useEffect(() => {
    if (!taskType || !node) return
    const next = { ...(taskType.default_config || {}), ...(node.data?.config || {}) }
    setLocalConfig(next)
  }, [node?.id, taskType?.id])

  const update = useCallback(
    (key, value) => {
      const next = { ...localConfig, [key]: value }
      setLocalConfig(next)
      onConfigChange?.(next)
    },
    [localConfig, onConfigChange]
  )

  if (!node || !taskType) return null

  const configKeys = Object.keys(defaultConfig)

  return (
    <div className="flex h-full flex-col border-l border-slate-700 bg-slate-800/95 shadow-xl">
      <div className="flex items-center justify-between border-b border-slate-700 px-3 py-2">
        <h3 className="text-sm font-semibold text-slate-200">Node config</h3>
        <button
          type="button"
          onClick={onClose}
          className="rounded p-1.5 text-slate-400 hover:bg-slate-700 hover:text-white"
          aria-label="Close"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-3">
        <p className="mb-3 text-xs text-slate-500">{taskType.label}</p>
        <div className="space-y-3">
          {configKeys.map((key) => {
            const val = localConfig[key]
            const isBool = typeof defaultConfig[key] === 'boolean'
            const isBackend = key === 'backend'

            if (isBackend && Array.isArray(supportedBackends) && supportedBackends.length > 0) {
              return (
                <label key={key} className="block">
                  <span className="block text-xs font-medium text-slate-400 mb-1">{fieldLabel(key)}</span>
                  <select
                    value={val ?? 'local'}
                    onChange={(e) => update(key, e.target.value)}
                    className="w-full rounded border border-slate-600 bg-slate-700 px-2 py-1.5 text-sm text-slate-200"
                  >
                    {supportedBackends.map((b) => (
                      <option key={b} value={b}>
                        {b === 'aws_eks' ? 'EKS (cloud)' : b === 'ibm_qpu' ? 'IBM QPU' : b}
                      </option>
                    ))}
                  </select>
                </label>
              )
            }
            if (isBool) {
              return (
                <label key={key} className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={!!val}
                    onChange={(e) => update(key, e.target.checked)}
                    className="rounded border-slate-600 text-sky-500"
                  />
                  <span className="text-sm text-slate-300">{fieldLabel(key)}</span>
                </label>
              )
            }
            if (key === 'routing_method') {
              return (
                <label key={key} className="block">
                  <span className="block text-xs font-medium text-slate-400 mb-1">{fieldLabel(key)}</span>
                  <select
                    value={val ?? 'qaoa'}
                    onChange={(e) => update(key, e.target.value)}
                    className="w-full rounded border border-slate-600 bg-slate-700 px-2 py-1.5 text-sm text-slate-200"
                  >
                    <option value="qaoa">QAOA</option>
                    <option value="rl">RL</option>
                    <option value="exact">Exact</option>
                  </select>
                </label>
              )
            }
            if (typeof val === 'number') {
              return (
                <label key={key} className="block">
                  <span className="block text-xs font-medium text-slate-400 mb-1">{fieldLabel(key)}</span>
                  <input
                    type="number"
                    value={val}
                    onChange={(e) => update(key, e.target.value === '' ? defaultConfig[key] : Number(e.target.value))}
                    className="w-full rounded border border-slate-600 bg-slate-700 px-2 py-1.5 text-sm text-slate-200"
                  />
                </label>
              )
            }
            return (
              <label key={key} className="block">
                <span className="block text-xs font-medium text-slate-400 mb-1">{fieldLabel(key)}</span>
                <input
                  type="text"
                  value={val ?? ''}
                  onChange={(e) => update(key, e.target.value)}
                  className="w-full rounded border border-slate-600 bg-slate-700 px-2 py-1.5 text-sm text-slate-200"
                />
              </label>
            )
          })}
        </div>
      </div>
    </div>
  )
}

export default ConfigDrawer
