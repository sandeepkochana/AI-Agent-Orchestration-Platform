import { useEffect, useState } from 'react'
import { Plus, Bot, Trash2, Edit2, Play, MessageSquare } from 'lucide-react'
import { agentApi } from '../api/client'
import type { Agent } from '../api/client'
import AgentForm from '../components/AgentForm'
import toast from 'react-hot-toast'

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [showForm, setShowForm] = useState(false)
  const [editAgent, setEditAgent] = useState<Agent | null>(null)
  const [running, setRunning] = useState<string | null>(null)
  const [chatAgent, setChatAgent] = useState<Agent | null>(null)
  const [chatMsg, setChatMsg] = useState('')
  const [chatHistory, setChatHistory] = useState<{ role: string; content: string }[]>([])

  const load = () => agentApi.list().then(setAgents)
  useEffect(() => { load() }, [])

  const handleSave = (agent: Agent) => {
    setShowForm(false)
    setEditAgent(null)
    load()
    toast.success('Agent saved!')
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this agent?')) return
    await agentApi.delete(id)
    load()
    toast.success('Agent deleted')
  }

  const handleRun = async (agent: Agent) => {
    const msg = prompt('Enter a message for the agent:')
    if (!msg) return
    setRunning(agent.id)
    try {
      const result = await agentApi.run(agent.id, msg)
      toast.success(`Done! ${result.tokens} tokens used.`)
      alert(`Response:\n\n${result.output}`)
    } catch (e: unknown) {
      toast.error('Agent run failed')
    } finally {
      setRunning(null)
    }
  }

  const handleChat = async () => {
    if (!chatAgent || !chatMsg.trim()) return
    const userMsg = chatMsg.trim()
    setChatMsg('')
    setChatHistory(h => [...h, { role: 'user', content: userMsg }])
    try {
      const result = await agentApi.run(chatAgent.id, userMsg, chatAgent.id)
      setChatHistory(h => [...h, { role: 'assistant', content: result.output }])
    } catch {
      setChatHistory(h => [...h, { role: 'assistant', content: '❌ Error running agent.' }])
    }
  }

  return (
    <div className="p-8 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Agents</h1>
          <p className="text-gray-400 text-sm mt-1">Create and manage your AI agents</p>
        </div>
        <button onClick={() => { setEditAgent(null); setShowForm(true) }} className="btn-primary flex items-center gap-2">
          <Plus size={16} /> New Agent
        </button>
      </div>

      {(showForm || editAgent) && (
        <AgentForm
          agent={editAgent}
          onSave={handleSave}
          onCancel={() => { setShowForm(false); setEditAgent(null) }}
        />
      )}

      {agents.length === 0 && !showForm && (
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-10 text-center">
          <Bot size={40} className="mx-auto text-gray-600 mb-3" />
          <p className="text-gray-400">No agents yet. Create your first agent to get started.</p>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4">
        {agents.map(agent => (
          <div key={agent.id} className="bg-gray-900 rounded-xl border border-gray-800 p-5 hover:border-gray-600 transition-colors">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-brand-600/20 flex items-center justify-center">
                  <Bot size={20} className="text-brand-400" />
                </div>
                <div>
                  <h3 className="font-semibold text-white">{agent.name}</h3>
                  <p className="text-xs text-gray-400 capitalize">{agent.role} · {agent.model}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${agent.is_active ? 'bg-green-400' : 'bg-gray-600'}`} />
              </div>
            </div>

            <p className="text-sm text-gray-400 mt-3 line-clamp-2">{agent.system_prompt}</p>

            <div className="flex flex-wrap gap-2 mt-3">
              {agent.tools.map(t => (
                <span key={t} className="text-xs bg-gray-800 text-gray-300 px-2 py-0.5 rounded">{t}</span>
              ))}
              {agent.channels.map(c => (
                <span key={c} className="text-xs bg-purple-900/50 text-purple-300 px-2 py-0.5 rounded border border-purple-700">{c}</span>
              ))}
            </div>

            <div className="flex gap-2 mt-4">
              <button
                onClick={() => { setChatAgent(agent); setChatHistory([]) }}
                className="btn-ghost text-xs flex items-center gap-1"
              >
                <MessageSquare size={13} /> Chat
              </button>
              <button
                onClick={() => handleRun(agent)}
                disabled={running === agent.id}
                className="btn-ghost text-xs flex items-center gap-1"
              >
                <Play size={13} /> {running === agent.id ? 'Running…' : 'Run'}
              </button>
              <button
                onClick={() => { setEditAgent(agent); setShowForm(false) }}
                className="btn-ghost text-xs flex items-center gap-1"
              >
                <Edit2 size={13} /> Edit
              </button>
              <button
                onClick={() => handleDelete(agent.id)}
                className="btn-ghost text-xs text-red-400 hover:text-red-300 flex items-center gap-1"
              >
                <Trash2 size={13} /> Delete
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Inline Chat Panel */}
      {chatAgent && (
        <div className="fixed bottom-0 right-0 w-96 h-[500px] bg-gray-900 border border-gray-700 rounded-tl-xl flex flex-col shadow-2xl z-50">
          <div className="p-3 border-b border-gray-700 flex justify-between items-center">
            <div className="flex items-center gap-2">
              <Bot size={16} className="text-brand-400" />
              <span className="text-sm font-semibold">{chatAgent.name}</span>
            </div>
            <button onClick={() => setChatAgent(null)} className="text-gray-500 hover:text-white text-xs">✕</button>
          </div>
          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            {chatHistory.length === 0 && (
              <p className="text-gray-600 text-xs text-center mt-10">Send a message to start chatting.</p>
            )}
            {chatHistory.map((m, i) => (
              <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[80%] text-sm px-3 py-2 rounded-xl ${
                  m.role === 'user'
                    ? 'bg-brand-600 text-white rounded-br-none'
                    : 'bg-gray-800 text-gray-200 rounded-bl-none'
                }`}>
                  {m.content}
                </div>
              </div>
            ))}
          </div>
          <div className="p-3 border-t border-gray-700 flex gap-2">
            <input
              className="input flex-1 text-sm"
              placeholder="Type a message…"
              value={chatMsg}
              onChange={e => setChatMsg(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleChat()}
            />
            <button onClick={handleChat} className="btn-primary text-sm px-3">Send</button>
          </div>
        </div>
      )}
    </div>
  )
}
