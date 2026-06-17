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

const RESPONSE_FORMATS = ['any', 'plain text', 'markdown', 'JSON']
const TONES = ['any', 'professional', 'casual', 'concise', 'detailed']

const EMPTY: Partial<Agent> = {
  name: '', role: 'assistant', system_prompt: '', model: 'gpt-4o-mini',
  tools: [], skills: [], channels: [], memory_enabled: true, max_iterations: 10,
  temperature: 0.7, guardrails: {}, schedule: {}, interaction_rules: {},
}

export default function AgentForm({ agent, onSave, onCancel }: Props) {
  const [form, setForm] = useState<Partial<Agent>>(agent ?? EMPTY)
  const [availableTools, setAvailableTools] = useState<string[]>([])
  const [loading, setLoading] = useState(false)

  // Guardrail helpers
  const maxTokens: number = (form.guardrails as any)?.max_tokens ?? 0
  const bannedTopics: string = ((form.guardrails as any)?.banned_topics ?? []).join(', ')

  // Schedule helpers
  const schedEnabled: boolean = (form.schedule as any)?.enabled ?? false
  const schedCron: string = (form.schedule as any)?.cron ?? ''
  const schedPrompt: string = (form.schedule as any)?.prompt ?? ''

  // Interaction rules helpers
  const irFormat: string = (form.interaction_rules as any)?.response_format ?? 'any'
  const irTone: string = (form.interaction_rules as any)?.tone ?? 'any'
  const irCustom: string = (form.interaction_rules as any)?.custom_instructions ?? ''

  const setGuardrail = (key: string, val: unknown) =>
    setForm(f => ({ ...f, guardrails: { ...(f.guardrails as any), [key]: val } }))

  const setSchedule = (key: string, val: unknown) =>
    setForm(f => ({ ...f, schedule: { ...(f.schedule as any), [key]: val } }))

  const setIRule = (key: string, val: unknown) =>
    setForm(f => ({ ...f, interaction_rules: { ...(f.interaction_rules as any), [key]: val } }))

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
    <div className="bg-gray-900 rounded-xl border border-gray-700 p-6 space-y-5">
      <h2 className="text-lg font-semibold">{agent ? 'Edit Agent' : 'Create Agent'}</h2>

      {/* Name + Role */}
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

      {/* System Prompt */}
      <div>
        <label className="text-xs text-gray-400">System Prompt</label>
        <textarea
          className="input w-full mt-1 h-28 resize-none"
          value={form.system_prompt ?? ''}
          onChange={e => setForm(f => ({ ...f, system_prompt: e.target.value }))}
          placeholder="You are a helpful assistant..."
        />
      </div>

      {/* Model + Iterations + Temperature */}
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

      {/* Tools */}
      <div>
        <label className="text-xs text-gray-400 block mb-2">Tools</label>
        <div className="flex flex-wrap gap-2">
          {availableTools.map(t => (
            <button
              key={t} type="button" onClick={() => toggle('tools', t)}
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

      {/* Skills */}
      <div>
        <label className="text-xs text-gray-400 block mb-1">
          Skills <span className="text-gray-600">(comma-separated capability tags injected into system prompt)</span>
        </label>
        <input
          className="input w-full mt-1"
          value={((form.skills as string[]) || []).join(', ')}
          onChange={e =>
            setForm(f => ({
              ...f,
              skills: e.target.value.split(',').map(s => s.trim()).filter(Boolean),
            }))
          }
          placeholder="e.g. summarization, code review, translation"
        />
      </div>

      {/* Channels */}
      <div>
        <label className="text-xs text-gray-400 block mb-2">Channels</label>
        <div className="flex gap-2">
          {CHANNELS_OPTIONS.map(c => (
            <button
              key={c} type="button" onClick={() => toggle('channels', c)}
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

      {/* Memory */}
      <div className="flex items-center gap-3">
        <label className="text-xs text-gray-400">Memory</label>
        <button
          type="button"
          onClick={() => setForm(f => ({ ...f, memory_enabled: !f.memory_enabled }))}
          className={`w-10 h-5 rounded-full transition-colors ${form.memory_enabled ? 'bg-brand-500' : 'bg-gray-700'}`}
        >
          <div className={`w-4 h-4 bg-white rounded-full m-0.5 transition-transform ${form.memory_enabled ? 'translate-x-5' : ''}`} />
        </button>
        <span className="text-xs text-gray-500">Persist conversation history per thread</span>
      </div>

      {/* ── Guardrails ─────────────────────────────────────────────────── */}
      <div className="border border-gray-700 rounded-lg p-4 space-y-3">
        <p className="text-xs font-semibold text-gray-300 uppercase tracking-wider">Guardrails</p>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-xs text-gray-400">Max Tokens <span className="text-gray-600">(0 = unlimited)</span></label>
            <input
              type="number" className="input w-full mt-1" min={0} step={100}
              value={maxTokens}
              onChange={e => setGuardrail('max_tokens', +e.target.value || 0)}
              placeholder="e.g. 2000"
            />
          </div>
          <div>
            <label className="text-xs text-gray-400">Banned Topics <span className="text-gray-600">(comma-separated)</span></label>
            <input
              className="input w-full mt-1"
              value={bannedTopics}
              onChange={e =>
                setGuardrail(
                  'banned_topics',
                  e.target.value.split(',').map(s => s.trim()).filter(Boolean)
                )
              }
              placeholder="e.g. politics, gambling"
            />
          </div>
        </div>
      </div>

      {/* ── Schedule ───────────────────────────────────────────────────── */}
      <div className="border border-gray-700 rounded-lg p-4 space-y-3">
        <div className="flex items-center gap-3">
          <p className="text-xs font-semibold text-gray-300 uppercase tracking-wider">Schedule</p>
          <button
            type="button"
            onClick={() => setSchedule('enabled', !schedEnabled)}
            className={`w-10 h-5 rounded-full transition-colors ${schedEnabled ? 'bg-brand-500' : 'bg-gray-700'}`}
          >
            <div className={`w-4 h-4 bg-white rounded-full m-0.5 transition-transform ${schedEnabled ? 'translate-x-5' : ''}`} />
          </button>
        </div>
        {schedEnabled && (
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-gray-400">Cron Expression</label>
              <input
                className="input w-full mt-1 font-mono"
                value={schedCron}
                onChange={e => setSchedule('cron', e.target.value)}
                placeholder="e.g. 0 9 * * 1-5"
              />
              <p className="text-xs text-gray-600 mt-1">UTC. min hr dom mon dow</p>
            </div>
            <div>
              <label className="text-xs text-gray-400">Auto-run Prompt</label>
              <input
                className="input w-full mt-1"
                value={schedPrompt}
                onChange={e => setSchedule('prompt', e.target.value)}
                placeholder="e.g. Good morning! What's today's news?"
              />
            </div>
          </div>
        )}
      </div>

      {/* ── Interaction Rules ──────────────────────────────────────────── */}
      <div className="border border-gray-700 rounded-lg p-4 space-y-3">
        <p className="text-xs font-semibold text-gray-300 uppercase tracking-wider">Interaction Rules</p>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-xs text-gray-400">Response Format</label>
            <select
              className="input w-full mt-1"
              value={irFormat}
              onChange={e => setIRule('response_format', e.target.value)}
            >
              {RESPONSE_FORMATS.map(f => <option key={f} value={f}>{f === 'any' ? 'Any (no constraint)' : f}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-400">Tone</label>
            <select
              className="input w-full mt-1"
              value={irTone}
              onChange={e => setIRule('tone', e.target.value)}
            >
              {TONES.map(t => <option key={t} value={t}>{t === 'any' ? 'Any (no constraint)' : t}</option>)}
            </select>
          </div>
        </div>
        <div>
          <label className="text-xs text-gray-400">Custom Instructions <span className="text-gray-600">(appended to system prompt)</span></label>
          <textarea
            className="input w-full mt-1 h-16 resize-none text-xs"
            value={irCustom}
            onChange={e => setIRule('custom_instructions', e.target.value)}
            placeholder="e.g. Always start with a TL;DR. Never use bullet points."
          />
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-3 pt-1">
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
