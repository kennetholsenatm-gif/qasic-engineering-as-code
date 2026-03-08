import { memo } from 'react'
import { Handle, Position } from '@xyflow/react'

const BACKEND_LABELS = {
  local: 'Local',
  ibm_qpu: 'IBM QPU',
  aws_eks: 'EKS (cloud)',
}

function TaskNode({ data, selected }) {
  const taskType = data?.task_type || 'task'
  const label = data?.label || taskType
  const config = data?.config || {}
  const backend = config.backend || 'local'

  return (
    <div
      className={`rounded-lg border-2 px-3 py-2 min-w-[140px] bg-slate-800 text-slate-100 ${
        selected ? 'border-sky-500' : 'border-slate-600'
      } ${data?.invalid ? 'border-red-500' : ''}`}
    >
      <Handle type="target" position={Position.Left} id="input" className="!w-2 !h-2 !bg-sky-400" />
      <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">
        {BACKEND_LABELS[backend] || backend}
        {backend === 'aws_eks' && <span className="ml-1 text-slate-500 normal-case">(coming soon)</span>}
      </div>
      <div className="font-medium text-sm mt-0.5">{label}</div>
      <Handle type="source" position={Position.Right} id="output" className="!w-2 !h-2 !bg-sky-400" />
    </div>
  )
}

export default memo(TaskNode)
