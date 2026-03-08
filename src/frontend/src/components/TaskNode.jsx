import { memo } from 'react'
import { Handle, Position } from '@xyflow/react'

const BACKEND_LABELS = {
  local: 'Local',
  ibm_qpu: 'IBM QPU',
  aws_eks: 'EKS (cloud)',
}

const COMPUTE_BADGES = {
  classical_sim: {
    label: 'Sim',
    className: 'bg-slate-500/20 text-slate-300 ring-1 ring-slate-500/30',
  },
  fdtf: {
    label: 'FDTD',
    className: 'bg-amber-500/20 text-amber-300 ring-1 ring-amber-500/30',
  },
  quantum_backend: {
    label: 'QPU',
    className: 'bg-violet-500/20 text-violet-300 ring-1 ring-violet-500/30',
  },
  eks: {
    label: 'EKS',
    className: 'bg-emerald-500/20 text-emerald-300 ring-1 ring-emerald-500/30',
  },
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
      className={`
        rounded-xl border-2 px-3 py-2 min-w-[140px]
        bg-slate-800/90 backdrop-blur-sm
        shadow-md shadow-black/20
        transition-all duration-200 ease-in-out
        hover:-translate-y-0.5 hover:border-slate-400
        ${selected ? 'ring-2 ring-sky-500 shadow-lg shadow-sky-500/20 border-sky-500' : 'border-slate-600'}
        ${data?.invalid ? 'border-red-500 ring-2 ring-red-500/50' : ''}
      `}
    >
      <Handle
        type="target"
        position={Position.Left}
        id="input"
        className="!w-3 !h-3 !border-2 !-left-1.5 !border-sky-400 !bg-slate-600"
      />
      <div className="flex items-center gap-1.5 flex-wrap">
        <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">
          {BACKEND_LABELS[backend] || backend}
          {backend === 'aws_eks' && <span className="ml-1 text-slate-500 normal-case">(soon)</span>}
        </span>
        {badge && (
          <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-md ${badge.className}`}>
            {badge.label}
          </span>
        )}
      </div>
      <div className="text-sm font-semibold text-slate-100 mt-0.5">{label}</div>
      <Handle
        type="source"
        position={Position.Right}
        id="output"
        className="!w-3 !h-3 !border-2 !-right-1.5 !border-sky-400 !bg-slate-600"
      />
    </div>
  )
}

export default memo(TaskNode)
