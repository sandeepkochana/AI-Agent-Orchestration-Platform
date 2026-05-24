import { useEffect, useState } from 'react'
import { execApi } from '../api/client'
import type { Execution, ExecLog } from '../api/client'
import LogViewer from '../components/LogViewer'
import { useStore } from '../store/useStore'
import { RefreshCw, Trash2 } from 'lucide-react'

export default function MonitorPage() {
  const [executions, setExecutions] = useState<Execution[]>([])
  const [selectedExec, setSelectedExec] = useState<Execution | null>(null)
  const [execLogs, setExecLogs] = useState<ExecLog[]>([])
  const liveLogs = useStore(s => s.liveLogs)
  const clearLogs = useStore(s => s.clearLogs)

  const load = () => execApi.list(50).then(setExecutions)

  useEffect(() => { load() }, [])

  const selectExec = async (exec: Execution) => {
    setSelectedExec(exec)
    const logs = await execApi.logs(exec.id)
    setExecLogs(logs)
  }

  const totalTokens = executions.reduce((s, e) => s + e.total_tokens, 0)
  const totalCost = executions.reduce((s, e) => s + e.total_cost, 0)

  return (
    <div className="p-6 space-y-4">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Monitor</h1>
          <p className="text-gray-400 text-sm">Real-time execution logs and performance metrics</p>
        </div>
        <button onClick={load} className="btn-ghost text-xs flex items-center gap-1">
          <RefreshCw size={13} /> Refresh
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-3">
        {[
          { label: 'Total Runs', value: executions.length },
          { label: 'Completed', value: executions.filter(e => e.status === 'completed').length },
          { label: 'Total Tokens', value: totalTokens.toLocaleString() },
          { label: 'Estimated Cost', value: `$${totalCost.toFixed(4)}` },
        ].map(({ label, value }) => (
          <div key={label} className="bg-gray-900 rounded-xl border border-gray-800 p-4">
            <div className="text-xs text-gray-400 mb-1">{label}</div>
            <div className="text-xl font-bold font-mono">{value}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* Execution list */}
        <div className="bg-gray-900 rounded-xl border border-gray-800">
          <div className="p-3 border-b border-gray-800 text-sm font-semibold">Execution History</div>
          <div className="overflow-y-auto max-h-80">
            {executions.length === 0 && (
              <p className="text-gray-600 text-sm p-4">No executions yet.</p>
            )}
            {executions.map(e => (
              <button
                key={e.id}
                onClick={() => selectExec(e)}
                className={`w-full text-left px-4 py-3 border-b border-gray-800 last:border-0 hover:bg-gray-800 transition-colors ${
                  selectedExec?.id === e.id ? 'bg-gray-800' : ''
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${
                      e.status === 'completed' ? 'bg-green-400'
                      : e.status === 'failed' ? 'bg-red-400'
                      : 'bg-yellow-400 animate-pulse'
                    }`} />
                    <span className="text-sm text-gray-300 truncate max-w-[180px]">
                      {e.input_message || 'Workflow'}
                    </span>
                  </div>
                  <div className="text-right">
                    <div className="text-xs text-gray-500">{new Date(e.started_at).toLocaleTimeString()}</div>
                    <div className="text-xs text-gray-600">{e.total_tokens} tok</div>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Execution detail */}
        <div className="bg-gray-900 rounded-xl border border-gray-800">
          <div className="p-3 border-b border-gray-800 text-sm font-semibold">
            {selectedExec ? `Execution: ${selectedExec.id.slice(0, 8)}…` : 'Select an execution'}
          </div>
          {selectedExec && (
            <div className="p-3 space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-400">Status</span>
                <span className={
                  selectedExec.status === 'completed' ? 'text-green-400'
                  : selectedExec.status === 'failed' ? 'text-red-400'
                  : 'text-yellow-400'
                }>{selectedExec.status}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Tokens</span>
                <span className="font-mono">{selectedExec.total_tokens}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Cost</span>
                <span className="font-mono">${selectedExec.total_cost.toFixed(5)}</span>
              </div>
              <div className="pt-2 border-t border-gray-800">
                <div className="text-xs text-gray-400 mb-1">Output</div>
                <p className="text-xs text-gray-300 bg-gray-800 rounded p-2 max-h-24 overflow-y-auto">
                  {selectedExec.output_message || '—'}
                </p>
              </div>
              {execLogs.length > 0 && (
                <div className="pt-2 border-t border-gray-800">
                  <div className="text-xs text-gray-400 mb-1">Step Logs</div>
                  <LogViewer logs={execLogs} className="max-h-32 bg-gray-950 rounded" />
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Live logs */}
      <div className="bg-gray-900 rounded-xl border border-gray-800">
        <div className="p-3 border-b border-gray-800 flex justify-between items-center">
          <div className="flex items-center gap-2 text-sm font-semibold">
            <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
            Live Feed
            <span className="text-xs text-gray-500">({liveLogs.length} events)</span>
          </div>
          <button onClick={clearLogs} className="text-xs text-gray-500 hover:text-gray-300 flex items-center gap-1">
            <Trash2 size={12} /> Clear
          </button>
        </div>
        <LogViewer logs={liveLogs} className="h-64 bg-gray-950" />
      </div>
    </div>
  )
}
