import { memo } from 'react'
import { Handle, Position } from '@xyflow/react'

const STAGE_LABELS = {
  tofu_init: 'Tofu init',
  tofu_plan: 'Tofu plan',
  tofu_apply: 'Tofu apply',
  tofu_destroy: 'Tofu destroy',
  approval: 'Approval',
  script: 'Script',
}

function StageNode({ data, selected }) {
  const stageType = data?.stage_type || 'script'
  const label = data?.label || STAGE_LABELS[stageType] || stageType

  return (
    <div
      className={`rounded-lg border-2 px-3 py-2 min-w-[140px] bg-slate-800 text-slate-100 ${
        selected ? 'border-sky-500' : 'border-slate-600'
      } ${data?.invalid ? 'border-red-500' : ''}`}
    >
      <Handle type="target" position={Position.Left} id="input" className="!w-2 !h-2 !bg-sky-400" />
      <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">
        {STAGE_LABELS[stageType] || stageType}
      </div>
      <div className="font-medium text-sm mt-0.5">{label}</div>
      <Handle type="source" position={Position.Right} id="output" className="!w-2 !h-2 !bg-sky-400" />
    </div>
  )
}

export default memo(StageNode)
