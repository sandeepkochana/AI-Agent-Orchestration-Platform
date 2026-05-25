import { useCallback, useEffect, useState } from 'react'
import {
  ReactFlow, Background, Controls, MiniMap,
  addEdge, useNodesState, useEdgesState, BackgroundVariant,
  type Connection,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { Plus, Save, Play, GitBranch, LayoutTemplate, GitFork, X } from 'lucide-react'
import { workflowApi, agentApi } from '../api/client'
import type { Workflow, Agent } from '../api/client'
import { nodeTypes } from '../components/WorkflowNodes'
import toast from 'react-hot-toast'

// Simple ID generator
const genId = () => Math.random().toString(36).slice(2)

export default function WorkflowBuilderPage() {
  const [workflows, setWorkflows] = useState<Workflow[]>([])
  const [selected, setSelected] = useState<Workflow | null>(null)
  const [agents, setAgents] = useState<Agent[]>([])
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [running, setRunning] = useState(false)
  const [runInput, setRunInput] = useState('')
  const [runOutput, setRunOutput] = useState<{ output: string; tokens: number } | null>(null)
  const [templates, setTemplates] = useState<unknown[]>([])
  const [showTemplates, setShowTemplates] = useState(false)

  // ── Condition node modal ────────────────────────────────────────────────────
  const [showConditionModal, setShowConditionModal] = useState(false)
  const [conditionDraft, setConditionDraft] = useState({
    label: 'Quality Check',
    condition_prompt: '',
  })

  useEffect(() => {
    workflowApi.list().then(setWorkflows)
    agentApi.list().then(setAgents)
    workflowApi.templates().then(setTemplates)
  }, [])

  const loadWorkflow = (wf: Workflow) => {
    setSelected(wf)
    setName(wf.name)
    setDescription(wf.description)
    setNodes(wf.nodes as never[])
    setEdges(wf.edges as never[])
    setRunOutput(null)
  }

  const newWorkflow = () => {
    setSelected(null)
    setName('New Workflow')
    setDescription('')
    setNodes([
      { id: 'start-1', type: 'start', position: { x: 100, y: 200 }, data: { label: 'Start' } },
      { id: 'end-1', type: 'end', position: { x: 700, y: 200 }, data: { label: 'End' } },
    ] as never[])
    setEdges([])
    setRunOutput(null)
  }

  // Opens the modal; actual node creation happens in confirmConditionNode
  const openConditionModal = () => {
    setConditionDraft({ label: 'Quality Check', condition_prompt: '' })
    setShowConditionModal(true)
  }

  const confirmConditionNode = () => {
    const id = `condition-${genId()}`
    setNodes(ns => [...ns, {
      id,
      type: 'condition',
      position: { x: 350 + Math.random() * 200, y: 150 + Math.random() * 100 },
      data: {
        label: conditionDraft.label,
        condition_prompt: conditionDraft.condition_prompt,
      },
    } as never])
    setShowConditionModal(false)
    toast.success('Condition node added — connect the green (T) and red (F) handles.')
  }

  const addAgentNode = (agent: Agent) => {
    const id = `agent-${genId()}`
    setNodes(ns => [...ns, {
      id,
      type: 'agent',
      position: { x: 300 + Math.random() * 200, y: 150 + Math.random() * 100 },
      data: {
        label: agent.name,
        agent_id: agent.id,
        role: agent.role,
        model: agent.model,
        tools: agent.tools,
      },
    } as never])
  }

  const onConnect = useCallback((conn: Connection) => {
    setEdges(es => addEdge({ ...conn, id: `e-${genId()}` }, es))
  }, [setEdges])

  const save = async () => {
    const payload = { name, description, nodes, edges, trigger: { type: 'manual' } }
    try {
      if (selected) {
        const updated = await workflowApi.update(selected.id, payload)
        setSelected(updated)
        toast.success('Workflow saved!')
      } else {
        const created = await workflowApi.create(payload)
        setSelected(created)
        toast.success('Workflow created!')
      }
      workflowApi.list().then(setWorkflows)
    } catch {
      toast.error('Save failed')
    }
  }

  const run = async () => {
    if (!selected) { toast.error('Save the workflow first'); return }
    if (!runInput.trim()) { toast.error('Enter an input message below the toolbar'); return }
    setRunning(true)
    setRunOutput(null)
    try {
      const result = await workflowApi.run(selected.id, runInput)
      setRunOutput({ output: result.output, tokens: result.tokens })
      toast.success(`Completed · ${result.tokens} tokens`)
    } catch {
      toast.error('Workflow run failed')
    } finally {
      setRunning(false)
    }
  }

  const loadTemplate = (tpl: Record<string, unknown>) => {
    setSelected(null)
    setName(tpl.name as string)
    setDescription(tpl.description as string)
    setNodes(tpl.nodes as never[])
    setEdges(tpl.edges as never[])
    setShowTemplates(false)
    setRunOutput(null)
    toast.success(`Template "${tpl.name}" loaded — assign agents to nodes, then save.`)
  }

  return (
    <div className="flex h-[calc(100vh-0px)] relative">
      {/* ── Condition node modal ──────────────────────────────────────────── */}
      {showConditionModal && (
        <div className="absolute inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-5 w-[440px] space-y-4 shadow-2xl">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <GitFork size={16} className="text-yellow-400" />
                <h3 className="font-semibold text-sm">Add Condition Node</h3>
              </div>
              <button onClick={() => setShowConditionModal(false)} className="text-gray-500 hover:text-gray-300">
                <X size={16} />
              </button>
            </div>

            <div>
              <label className="text-xs text-gray-400">Label</label>
              <input
                className="input w-full mt-1"
                value={conditionDraft.label}
                onChange={e => setConditionDraft(d => ({ ...d, label: e.target.value }))}
                placeholder="e.g. Quality Check"
              />
            </div>

            <div>
              <label className="text-xs text-gray-400">
                Condition <span className="text-gray-600">(LLM evaluates this as true/false)</span>
              </label>
              <textarea
                className="input w-full mt-1 h-24 resize-none text-sm"
                value={conditionDraft.condition_prompt}
                onChange={e => setConditionDraft(d => ({ ...d, condition_prompt: e.target.value }))}
                placeholder="Is the response at least 3 sentences long, well-structured, and directly answering the question?"
                autoFocus
              />
              <p className="text-[10px] text-gray-600 mt-1">
                Green handle (T) → pass / exit path · Red handle (F) → retry / loop path
              </p>
            </div>

            <div className="flex gap-2 pt-1">
              <button
                onClick={confirmConditionNode}
                disabled={!conditionDraft.condition_prompt.trim()}
                className="btn-primary flex-1 text-sm"
              >
                Add to Canvas
              </button>
              <button
                onClick={() => setShowConditionModal(false)}
                className="btn-ghost flex-1 text-sm"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Left panel ───────────────────────────────────────────────────── */}
      <div className="w-64 bg-gray-900 border-r border-gray-800 flex flex-col">
        <div className="p-4 border-b border-gray-800 flex justify-between items-center">
          <span className="font-semibold text-sm">Workflows</span>
          <button onClick={newWorkflow} className="text-brand-400 hover:text-brand-300">
            <Plus size={16} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          <button
            onClick={() => setShowTemplates(!showTemplates)}
            className="w-full flex items-center gap-2 text-xs text-purple-400 hover:text-purple-300 px-2 py-1.5"
          >
            <LayoutTemplate size={13} /> Templates
          </button>

          {showTemplates && (templates as Record<string, unknown>[]).map(t => (
            <button
              key={t.id as string}
              onClick={() => loadTemplate(t)}
              className="w-full text-left px-3 py-2 text-xs rounded bg-gray-800 hover:bg-gray-700 text-gray-300 ml-2"
            >
              📋 {t.name as string}
            </button>
          ))}

          <div className="border-t border-gray-800 my-2" />

          {workflows.map(wf => (
            <button
              key={wf.id}
              onClick={() => loadWorkflow(wf)}
              className={`w-full text-left px-3 py-2 rounded text-sm transition-colors ${
                selected?.id === wf.id
                  ? 'bg-brand-600/20 text-brand-300 border border-brand-700'
                  : 'text-gray-400 hover:bg-gray-800'
              }`}
            >
              <GitBranch size={12} className="inline mr-2" />
              {wf.name}
            </button>
          ))}
        </div>

        {/* Node palette */}
        <div className="border-t border-gray-800 p-3">
          <p className="text-xs text-gray-500 mb-2">Add to canvas:</p>
          <div className="space-y-1 max-h-36 overflow-y-auto mb-2">
            {agents.map(a => (
              <button
                key={a.id}
                onClick={() => addAgentNode(a)}
                className="w-full text-left text-xs bg-gray-800 hover:bg-gray-700 rounded px-2 py-1.5 text-gray-300 truncate"
              >
                🤖 {a.name}
              </button>
            ))}
          </div>
          <button
            onClick={openConditionModal}
            className="w-full text-left text-xs bg-yellow-950 hover:bg-yellow-900 border border-yellow-800 rounded px-2 py-1.5 text-yellow-300 flex items-center gap-1.5"
          >
            <GitFork size={12} /> Add Condition Node
          </button>
          <p className="text-[10px] text-gray-600 mt-1.5 leading-tight">
            Connects green (T) → pass, red (F) → retry/loop.
          </p>
        </div>
      </div>

      {/* ── Canvas area ──────────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col">
        {/* Toolbar row */}
        <div className="bg-gray-900 border-b border-gray-800 px-4 py-2 flex items-center gap-3">
          <input
            className="input text-sm w-44"
            placeholder="Workflow name"
            value={name}
            onChange={e => setName(e.target.value)}
          />
          <input
            className="input text-sm w-48"
            placeholder="Description (optional)"
            value={description}
            onChange={e => setDescription(e.target.value)}
          />
          <button onClick={save} className="btn-ghost text-xs flex items-center gap-1 shrink-0">
            <Save size={13} /> Save
          </button>

          {selected && (
            <>
              <div className="h-4 border-l border-gray-700 shrink-0" />
              <input
                className="input text-sm flex-1 min-w-36"
                placeholder="Input message — then hit Run ▶"
                value={runInput}
                onChange={e => setRunInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && run()}
              />
              <button
                onClick={run}
                disabled={running}
                className="btn-primary text-xs flex items-center gap-1 shrink-0"
              >
                <Play size={13} /> {running ? 'Running…' : 'Run'}
              </button>
            </>
          )}
        </div>

        {/* Inline run output */}
        {runOutput && (
          <div className="bg-gray-950 border-b border-gray-800 px-4 py-2">
            <div className="flex justify-between items-center mb-1">
              <span className="text-xs text-gray-400 font-mono">
                ✅ Output · {runOutput.tokens} tokens
              </span>
              <button
                onClick={() => setRunOutput(null)}
                className="text-xs text-gray-600 hover:text-gray-400 flex items-center gap-1"
              >
                <X size={11} /> clear
              </button>
            </div>
            <p className="text-sm text-gray-200 max-h-32 overflow-y-auto whitespace-pre-wrap leading-relaxed">
              {runOutput.output}
            </p>
          </div>
        )}

        {/* ReactFlow canvas */}
        <div className="flex-1">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            nodeTypes={nodeTypes}
            fitView
            colorMode="dark"
          >
            <Background variant={BackgroundVariant.Dots} gap={20} color="#1e293b" />
            <Controls />
            <MiniMap nodeColor="#4f6ef7" maskColor="rgba(15,23,42,0.8)" />
          </ReactFlow>
        </div>
      </div>
    </div>
  )
}
