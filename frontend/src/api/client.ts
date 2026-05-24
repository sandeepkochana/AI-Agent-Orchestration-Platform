import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

// ── Types ─────────────────────────────────────────────────────────────────────

export interface Agent {
  id: string
  name: string
  role: string
  system_prompt: string
  model: string
  tools: string[]
  channels: string[]
  memory_enabled: boolean
  max_iterations: number
  temperature: number
  guardrails: Record<string, unknown>
  skills: string[]
  schedule: Record<string, unknown>
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface Workflow {
  id: string
  name: string
  description: string
  nodes: WorkflowNode[]
  edges: WorkflowEdge[]
  trigger: Record<string, unknown>
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface WorkflowNode {
  id: string
  type: string
  position: { x: number; y: number }
  data: Record<string, unknown>
}

export interface WorkflowEdge {
  id: string
  source: string
  target: string
  label?: string
}

export interface Execution {
  id: string
  workflow_id?: string
  agent_id?: string
  trigger_type: string
  input_message: string
  output_message: string
  status: string
  total_tokens: number
  total_cost: number
  started_at: string
  completed_at?: string
}

export interface ExecLog {
  id: string
  execution_id: string
  agent_id?: string
  agent_name: string
  log_type: string
  content: string
  metadata: Record<string, unknown>
  timestamp: string
}

export interface ChannelMessage {
  id: string
  agent_id?: string
  channel: string
  channel_user_id: string
  channel_chat_id: string
  direction: string
  content: string
  is_read: boolean
  metadata: Record<string, unknown>
  created_at: string
}

// ── Agents ────────────────────────────────────────────────────────────────────

export const agentApi = {
  list: () => api.get<Agent[]>('/agents/').then(r => r.data),
  get: (id: string) => api.get<Agent>(`/agents/${id}`).then(r => r.data),
  create: (data: Partial<Agent>) => api.post<Agent>('/agents/', data).then(r => r.data),
  update: (id: string, data: Partial<Agent>) => api.put<Agent>(`/agents/${id}`, data).then(r => r.data),
  delete: (id: string) => api.delete(`/agents/${id}`),
  run: (id: string, message: string, threadId?: string) =>
    api.post(`/agents/${id}/run`, { message, thread_id: threadId }).then(r => r.data),
  tools: () => api.get<string[]>('/agents/tools').then(r => r.data),
}

// ── Workflows ─────────────────────────────────────────────────────────────────

export const workflowApi = {
  list: () => api.get<Workflow[]>('/workflows/').then(r => r.data),
  get: (id: string) => api.get<Workflow>(`/workflows/${id}`).then(r => r.data),
  create: (data: Partial<Workflow>) => api.post<Workflow>('/workflows/', data).then(r => r.data),
  update: (id: string, data: Partial<Workflow>) => api.put<Workflow>(`/workflows/${id}`, data).then(r => r.data),
  delete: (id: string) => api.delete(`/workflows/${id}`),
  run: (id: string, inputMessage: string) =>
    api.post(`/workflows/${id}/run`, { input_message: inputMessage }).then(r => r.data),
  templates: () => api.get('/workflows/templates').then(r => r.data),
}

// ── Executions ────────────────────────────────────────────────────────────────

export const execApi = {
  list: (limit = 50) => api.get<Execution[]>(`/executions/?limit=${limit}`).then(r => r.data),
  get: (id: string) => api.get<Execution>(`/executions/${id}`).then(r => r.data),
  logs: (id: string) => api.get<ExecLog[]>(`/executions/${id}/logs`).then(r => r.data),
}

// ── Messages ──────────────────────────────────────────────────────────────────

export const msgApi = {
  list: (channel?: string) => api.get<ChannelMessage[]>(`/messages/${channel ? `?channel=${channel}` : ''}`).then(r => r.data),
}

export default api
