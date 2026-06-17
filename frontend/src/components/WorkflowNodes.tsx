import { memo } from 'react'
import { Handle, Position } from '@xyflow/react'
import { Bot, Play, Square, GitFork } from 'lucide-react'

interface NodeData {
  label: string
  agent_id?: string
  role?: string
  model?: string
  tools?: string[]
}

export const AgentNode = memo(({ data, selected }: { data: NodeData; selected: boolean }) => (
  <div className={`bg-gray-800 border-2 rounded-xl p-3 min-w-[160px] transition-colors ${
    selected ? 'border-brand-500' : 'border-gray-600'
  }`}>
    <Handle type="target" position={Position.Left} className="!bg-brand-500" />
    <div className="flex items-center gap-2 mb-1">
      <Bot size={14} className="text-brand-400" />
      <span className="text-sm font-semibold text-white truncate">{data.label}</span>
    </div>
    {data.role && <div className="text-xs text-gray-400 capitalize">{data.role}</div>}
    {data.model && <div className="text-xs text-gray-500">{data.model}</div>}
    {data.tools && data.tools.length > 0 && (
      <div className="flex flex-wrap gap-1 mt-2">
        {data.tools.map((t: string) => (
          <span key={t} className="text-[10px] bg-gray-700 text-gray-300 px-1.5 py-0.5 rounded">{t}</span>
        ))}
      </div>
    )}
    <Handle type="source" position={Position.Right} className="!bg-brand-500" />
  </div>
))

export const StartNode = memo(({ selected }: { selected: boolean }) => (
  <div className={`bg-green-900 border-2 rounded-xl p-3 flex items-center gap-2 transition-colors ${
    selected ? 'border-green-400' : 'border-green-700'
  }`}>
    <Play size={14} className="text-green-400" />
    <span className="text-sm font-semibold text-white">Start</span>
    <Handle type="source" position={Position.Right} className="!bg-green-500" />
  </div>
))

export const EndNode = memo(({ selected }: { selected: boolean }) => (
  <div className={`bg-red-900 border-2 rounded-xl p-3 flex items-center gap-2 transition-colors ${
    selected ? 'border-red-400' : 'border-red-700'
  }`}>
    <Handle type="target" position={Position.Left} className="!bg-red-500" />
    <Square size={14} className="text-red-400" />
    <span className="text-sm font-semibold text-white">End</span>
  </div>
))

export const ConditionNode = memo(({ data, selected }: { data: NodeData & { condition_prompt?: string }; selected: boolean }) => (
  <div className={`bg-yellow-950 border-2 rounded-xl p-3 min-w-[180px] relative transition-colors ${
    selected ? 'border-yellow-400' : 'border-yellow-700'
  }`}>
    <Handle type="target" position={Position.Left} className="!bg-yellow-500" />
    <div className="flex items-center gap-2 mb-1">
      <GitFork size={14} className="text-yellow-400" />
      <span className="text-sm font-semibold text-white truncate">{data.label || 'Condition'}</span>
    </div>
    {data.condition_prompt && (
      <div className="text-[10px] text-yellow-300/70 leading-tight mt-1 max-w-[160px] line-clamp-2">
        {data.condition_prompt}
      </div>
    )}
    {/* True handle (top) — connects to the "yes / pass" branch */}
    <Handle
      type="source" position={Position.Right} id="true"
      style={{ top: '30%' }}
      className="!bg-green-500 !w-3 !h-3"
    />
    {/* False handle (bottom) — connects to the "no / retry" branch */}
    <Handle
      type="source" position={Position.Right} id="false"
      style={{ top: '70%' }}
      className="!bg-red-500 !w-3 !h-3"
    />
    <div className="absolute right-[-18px] text-[9px] font-bold text-green-400" style={{ top: 'calc(30% - 6px)' }}>T</div>
    <div className="absolute right-[-18px] text-[9px] font-bold text-red-400" style={{ top: 'calc(70% - 6px)' }}>F</div>
  </div>
))

export const nodeTypes = {
  agent: AgentNode,
  start: StartNode,
  end: EndNode,
  condition: ConditionNode,
}
