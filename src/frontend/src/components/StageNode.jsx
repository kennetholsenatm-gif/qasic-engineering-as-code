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
      <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">
        {STAGE_LABELS[stageType] || stageType}
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

export default memo(StageNode)
