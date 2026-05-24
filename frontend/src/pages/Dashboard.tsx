import { useEffect, useState } from 'react'
import { Bot, GitBranch, Zap, TrendingUp } from 'lucide-react'
import { agentApi, workflowApi, execApi } from '../api/client'
import type { Execution } from '../api/client'
import { Link } from 'react-router-dom'

export default function Dashboard() {
  const [agentCount, setAgentCount] = useState(0)
  const [workflowCount, setWorkflowCount] = useState(0)
  const [recentExecs, setRecentExecs] = useState<Execution[]>([])

  useEffect(() => {
    agentApi.list().then(a => setAgentCount(a.length))
    workflowApi.list().then(w => setWorkflowCount(w.length))
    execApi.list(10).then(setRecentExecs)
  }, [])

  const completed = recentExecs.filter(e => e.status === 'completed').length
  const totalCost = recentExecs.reduce((s, e) => s + (e.total_cost || 0), 0)

  const stats = [
    { icon: Bot, label: 'Agents', value: agentCount, to: '/agents', color: 'text-brand-400' },
    { icon: GitBranch, label: 'Workflows', value: workflowCount, to: '/workflows', color: 'text-purple-400' },
    { icon: Zap, label: 'Executions', value: recentExecs.length, to: '/monitor', color: 'text-yellow-400' },
    { icon: TrendingUp, label: 'Success Rate', value: recentExecs.length ? `${Math.round(completed / recentExecs.length * 100)}%` : '—', to: '/monitor', color: 'text-green-400' },
  ]

  return (
    <div className="p-8 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <p className="text-gray-400 mt-1">AI Agent Orchestration Platform overview</p>
      </div>

      <div className="grid grid-cols-4 gap-4">
        {stats.map(({ icon: Icon, label, value, to, color }) => (
          <Link key={label} to={to} className="bg-gray-900 rounded-xl p-5 border border-gray-800 hover:border-gray-600 transition-colors">
            <div className="flex items-center justify-between mb-3">
              <span className="text-gray-400 text-sm">{label}</span>
              <Icon size={18} className={color} />
            </div>
            <div className="text-3xl font-bold text-white">{value}</div>
          </Link>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-5">
          <h2 className="font-semibold mb-4 text-sm text-gray-300">Recent Executions</h2>
          {recentExecs.length === 0 && <p className="text-gray-600 text-sm">No executions yet.</p>}
          <div className="space-y-2">
            {recentExecs.slice(0, 8).map(e => (
              <div key={e.id} className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${
                    e.status === 'completed' ? 'bg-green-400'
                    : e.status === 'failed' ? 'bg-red-400'
                    : 'bg-yellow-400 animate-pulse'
                  }`} />
                  <span className="text-gray-300 truncate max-w-[200px]">{e.input_message || 'Workflow run'}</span>
                </div>
                <span className="text-gray-500 text-xs">{new Date(e.started_at).toLocaleTimeString()}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-gray-900 rounded-xl border border-gray-800 p-5">
          <h2 className="font-semibold mb-4 text-sm text-gray-300">Token Usage</h2>
          <div className="space-y-3">
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-gray-400">Total Tokens</span>
                <span className="text-white font-mono">{recentExecs.reduce((s, e) => s + e.total_tokens, 0).toLocaleString()}</span>
              </div>
            </div>
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-gray-400">Estimated Cost</span>
                <span className="text-white font-mono">${totalCost.toFixed(4)}</span>
              </div>
            </div>
            <div className="pt-2 border-t border-gray-800">
              <Link to="/agents" className="btn-primary w-full text-center block mt-2">
                + Create Agent
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
