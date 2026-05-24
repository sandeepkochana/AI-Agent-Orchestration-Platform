import { memo } from 'react'
import { Handle, Position } from '@xyflow/react'
import { Bot, Play, Square } from 'lucide-react'

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

export const nodeTypes = {
  agent: AgentNode,
  start: StartNode,
  end: EndNode,
}
