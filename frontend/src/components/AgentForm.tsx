import { useState, useEffect } from 'react'
import type { Agent } from '../api/client'
import { agentApi } from '../api/client'

const MODELS = ['gpt-4o-mini', 'gpt-4o', 'gpt-4-turbo', 'gpt-3.5-turbo']
const CHANNELS_OPTIONS = ['telegram', 'slack']

interface Props {
  agent?: Agent | null
  onSave: (agent: Agent) => void
  onCancel: () => void
}

const EMPTY: Partial<Agent> = {
  name: '', role: 'assistant', system_prompt: '', model: 'gpt-4o-mini',
  tools: [], channels: [], memory_enabled: true, max_iterations: 10,
  temperature: 0.7, guardrails: {}, skills: [], schedule: {},
}

export default function AgentForm({ agent, onSave, onCancel }: Props) {
  const [form, setForm] = useState<Partial<Agent>>(agent ?? EMPTY)
  const [availableTools, setAvailableTools] = useState<string[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    agentApi.tools().then(setAvailableTools)
  }, [])

  const toggle = (field: 'tools' | 'channels', val: string) => {
    const arr = (form[field] as string[]) || []
    setForm(f => ({ ...f, [field]: arr.includes(val) ? arr.filter(x => x !== val) : [...arr, val] }))
  }

  const submit = async () => {
    setLoading(true)
    try {
      const result = agent?.id
        ? await agentApi.update(agent.id, form)
        : await agentApi.create(form)
      onSave(result)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-700 p-6 space-y-4">
      <h2 className="text-lg font-semibold">{agent ? 'Edit Agent' : 'Create Agent'}</h2>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="text-xs text-gray-400">Name</label>
          <input
            className="input w-full mt-1"
            value={form.name ?? ''}
            onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
            placeholder="e.g. Research Bot"
          />
        </div>
        <div>
          <label className="text-xs text-gray-400">Role</label>
          <input
            className="input w-full mt-1"
            value={form.role ?? ''}
            onChange={e => setForm(f => ({ ...f, role: e.target.value }))}
            placeholder="e.g. researcher"
          />
        </div>
      </div>

      <div>
        <label className="text-xs text-gray-400">System Prompt</label>
        <textarea
          className="input w-full mt-1 h-28 resize-none"
          value={form.system_prompt ?? ''}
          onChange={e => setForm(f => ({ ...f, system_prompt: e.target.value }))}
          placeholder="You are a helpful assistant..."
        />
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div>
          <label className="text-xs text-gray-400">Model</label>
          <select
            className="input w-full mt-1"
            value={form.model}
            onChange={e => setForm(f => ({ ...f, model: e.target.value }))}
          >
            {MODELS.map(m => <option key={m}>{m}</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs text-gray-400">Max Iterations</label>
          <input
            type="number" className="input w-full mt-1" min={1} max={50}
            value={form.max_iterations ?? 10}
            onChange={e => setForm(f => ({ ...f, max_iterations: +e.target.value }))}
          />
        </div>
        <div>
          <label className="text-xs text-gray-400">Temperature</label>
          <input
            type="number" className="input w-full mt-1" step={0.1} min={0} max={2}
            value={form.temperature ?? 0.7}
            onChange={e => setForm(f => ({ ...f, temperature: +e.target.value }))}
          />
        </div>
      </div>

      <div>
        <label className="text-xs text-gray-400 block mb-2">Tools</label>
        <div className="flex flex-wrap gap-2">
          {availableTools.map(t => (
            <button
              key={t}
              type="button"
              onClick={() => toggle('tools', t)}
              className={`px-3 py-1 rounded-full text-xs border transition-colors ${
                (form.tools || []).includes(t)
                  ? 'bg-brand-600 border-brand-500 text-white'
                  : 'border-gray-600 text-gray-400 hover:border-gray-400'
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="text-xs text-gray-400 block mb-2">Channels</label>
        <div className="flex gap-2">
          {CHANNELS_OPTIONS.map(c => (
            <button
              key={c}
              type="button"
              onClick={() => toggle('channels', c)}
              className={`px-3 py-1 rounded-full text-xs border transition-colors ${
                (form.channels || []).includes(c)
                  ? 'bg-green-700 border-green-500 text-white'
                  : 'border-gray-600 text-gray-400 hover:border-gray-400'
              }`}
            >
              {c}
            </button>
          ))}
        </div>
      </div>

      <div className="flex items-center gap-3">
        <label className="text-xs text-gray-400">Memory</label>
        <button
          type="button"
          onClick={() => setForm(f => ({ ...f, memory_enabled: !f.memory_enabled }))}
          className={`w-10 h-5 rounded-full transition-colors ${form.memory_enabled ? 'bg-brand-500' : 'bg-gray-700'}`}
        >
          <div className={`w-4 h-4 bg-white rounded-full m-0.5 transition-transform ${form.memory_enabled ? 'translate-x-5' : ''}`} />
        </button>
      </div>

      <div className="flex gap-3 pt-2">
        <button
          onClick={submit}
          disabled={loading || !form.name || !form.system_prompt}
          className="btn-primary flex-1"
        >
          {loading ? 'Saving…' : agent ? 'Update Agent' : 'Create Agent'}
        </button>
        <button onClick={onCancel} className="btn-ghost flex-1">Cancel</button>
      </div>
    </div>
  )
}
