import { create } from 'zustand'
import type { Agent, Workflow, Execution, ExecLog, ChannelMessage } from '../api/client'

interface WSEvent {
  type: string
  execution_id?: string
  agent_name?: string
  log_type?: string
  content?: string
  status?: string
  metadata?: Record<string, unknown>
  channel?: string
  direction?: string
  [key: string]: unknown
}

interface Store {
  // Data
  agents: Agent[]
  workflows: Workflow[]
  executions: Execution[]
  messages: ChannelMessage[]
  liveLogs: WSEvent[]

  // WebSocket
  ws: WebSocket | null
  wsConnected: boolean

  // Actions
  setAgents: (a: Agent[]) => void
  setWorkflows: (w: Workflow[]) => void
  setExecutions: (e: Execution[]) => void
  setMessages: (m: ChannelMessage[]) => void
  appendLog: (e: WSEvent) => void
  clearLogs: () => void
  connectWs: () => void
  disconnectWs: () => void
}

export const useStore = create<Store>((set, get) => ({
  agents: [],
  workflows: [],
  executions: [],
  messages: [],
  liveLogs: [],
  ws: null,
  wsConnected: false,

  setAgents: (agents) => set({ agents }),
  setWorkflows: (workflows) => set({ workflows }),
  setExecutions: (executions) => set({ executions }),
  setMessages: (messages) => set({ messages }),
  appendLog: (event) => set((s) => ({ liveLogs: [...s.liveLogs.slice(-499), event] })),
  clearLogs: () => set({ liveLogs: [] }),

  connectWs: () => {
    const { ws } = get()
    if (ws) return
    const socket = new WebSocket(`ws://${window.location.host}/ws`)
    socket.onopen = () => set({ wsConnected: true })
    socket.onclose = () => { set({ wsConnected: false, ws: null }); setTimeout(() => get().connectWs(), 3000) }
    socket.onmessage = (e) => {
      try {
        const event: WSEvent = JSON.parse(e.data)
        get().appendLog(event)
      } catch { /* ignore */ }
    }
    set({ ws: socket })
  },

  disconnectWs: () => {
    const { ws } = get()
    if (ws) { ws.close(); set({ ws: null, wsConnected: false }) }
  },
}))
