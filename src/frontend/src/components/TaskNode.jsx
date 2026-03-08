import { memo } from 'react'
import { Handle, Position } from '@xyflow/react'

const BACKEND_LABELS = {
  local: 'Local',
  ibm_qpu: 'IBM QPU',
  aws_eks: 'EKS (cloud)',
}

const COMPUTE_BADGES = {
  classical_sim: { label: 'Sim', className: 'bg-slate-600 text-slate-200' },
  fdtf: { label: 'FDTD', className: 'bg-amber-700/80 text-amber-200' },
  quantum_backend: { label: 'QPU', className: 'bg-violet-700/80 text-violet-200' },
  eks: { label: 'EKS', className: 'bg-emerald-700/80 text-emerald-200' },
}

function TaskNode({ data, selected }) {
  const taskType = data?.task_type || 'task'
  const label = data?.label || taskType
  const config = data?.config || {}
  const backend = config.backend || 'local'
  const computeResource = data?.compute_resource
  const badge = computeResource ? COMPUTE_BADGES[computeResource] : null

  return (
    <div
      className={`rounded-lg border-2 px-3 py-2 min-w-[140px] bg-slate-800 text-slate-100 ${
        selected ? 'border-sky-500 ring-1 ring-sky-500/30' : 'border-slate-600'
      } ${data?.invalid ? 'border-red-500' : ''}`}
    >
      <Handle type="target" position={Position.Left} id="input" className="!w-2 !h-2 !bg-sky-400" />
      <div className="flex items-center gap-1.5 flex-wrap">
        <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">
          {BACKEND_LABELS[backend] || backend}
          {backend === 'aws_eks' && <span className="ml-1 text-slate-500 normal-case">(soon)</span>}
        </span>
        {badge && (
          <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${badge.className}`}>
            {badge.label}
          </span>
        )}
      </div>
      <div className="font-medium text-sm mt-0.5">{label}</div>
      <Handle type="source" position={Position.Right} id="output" className="!w-2 !h-2 !bg-sky-400" />
    </div>
  )
}

export default memo(TaskNode)
