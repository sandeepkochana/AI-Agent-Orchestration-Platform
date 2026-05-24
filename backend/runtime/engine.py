"""
LangGraph-based agent runtime engine.

Architecture:
- Single-agent: uses create_react_agent with a ToolNode to handle tool calls.
- Multi-agent workflow: builds a StateGraph where each node is an agent.
  Agents communicate via the shared graph state (async message passing).
  Edges are derived from the workflow definition (nodes + edges from the UI).
"""

import asyncio
import logging
from typing import Annotated, Any, Optional
from datetime import datetime
from uuid import uuid4

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent
from typing_extensions import TypedDict

from config import settings
from runtime.tools import get_tools_for_agent

logger = logging.getLogger(__name__)


# ─── Shared State ──────────────────────────────────────────────────────────────

class WorkflowState(TypedDict):
    messages: Annotated[list, add_messages]
    current_agent: str
    execution_id: str
    metadata: dict


# ─── Cost tracking ─────────────────────────────────────────────────────────────

COST_PER_TOKEN = {
    "gpt-4o": {"input": 5e-6, "output": 15e-6},
    "gpt-4o-mini": {"input": 0.15e-6, "output": 0.6e-6},
    "gpt-4-turbo": {"input": 10e-6, "output": 30e-6},
    "gpt-3.5-turbo": {"input": 0.5e-6, "output": 1.5e-6},
}

def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    rates = COST_PER_TOKEN.get(model, {"input": 1e-6, "output": 2e-6})
    return input_tokens * rates["input"] + output_tokens * rates["output"]


# ─── Single-Agent Runner ────────────────────────────────────────────────────────

class AgentRunner:
    """Wraps a single agent (LangGraph ReAct) with logging & token tracking."""

    def __init__(self, agent_config, ws_manager=None, db_session=None):
        self.config = agent_config
        self.ws = ws_manager
        self.db = db_session

        self.llm = ChatOpenAI(
            model=agent_config.model,
            temperature=agent_config.temperature,
            api_key=settings.OPENAI_API_KEY,
        )
        self.tools = get_tools_for_agent(agent_config.tools or [])
        self.graph = create_react_agent(
            self.llm,
            self.tools,
            state_modifier=agent_config.system_prompt,
        )

    async def _emit(self, execution_id: str, log_type: str, content: str, metadata: dict = None):
        if self.ws:
            await self.ws.send_log(execution_id, self.config.name, log_type, content, metadata)

    async def run(
        self,
        message: str,
        execution_id: str,
        thread_id: Optional[str] = None,
        history: list = None,
    ) -> dict:
        cfg = {"configurable": {"thread_id": thread_id or str(uuid4())}}
        messages = history or []
        messages.append(HumanMessage(content=message))

        total_tokens = 0
        total_cost = 0.0
        final_output = ""

        await self._emit(execution_id, "message", f"▶ Agent **{self.config.name}** processing: {message}")

        try:
            async for event in self.graph.astream_events(
                {"messages": messages}, cfg, version="v1"
            ):
                kind = event["event"]
                name = event.get("name", "")

                if kind == "on_chat_model_stream":
                    chunk = event["data"].get("chunk")
                    if chunk and chunk.content:
                        final_output += chunk.content

                elif kind == "on_chat_model_end":
                    usage = event["data"].get("output", {})
                    if hasattr(usage, "usage_metadata"):
                        meta = usage.usage_metadata
                        inp = meta.get("input_tokens", 0)
                        out = meta.get("output_tokens", 0)
                        total_tokens += inp + out
                        total_cost += estimate_cost(self.config.model, inp, out)

                elif kind == "on_tool_start":
                    tool_input = event["data"].get("input", {})
                    await self._emit(execution_id, "tool_call",
                                     f"🔧 **{name}** called with: `{tool_input}`",
                                     {"tool": name, "input": tool_input})

                elif kind == "on_tool_end":
                    tool_output = str(event["data"].get("output", ""))[:500]
                    await self._emit(execution_id, "tool_result",
                                     f"✅ **{name}** result: {tool_output}",
                                     {"tool": name})

        except Exception as e:
            error_msg = f"Agent error: {str(e)}"
            logger.exception(error_msg)
            await self._emit(execution_id, "error", f"❌ {error_msg}")
            return {"output": error_msg, "tokens": 0, "cost": 0.0, "error": True}

        if not final_output:
            # Fallback: invoke instead of stream
            result = await self.graph.ainvoke({"messages": [HumanMessage(content=message)]}, cfg)
            msgs = result.get("messages", [])
            final_output = msgs[-1].content if msgs else ""

        await self._emit(execution_id, "message",
                         f"✅ **{self.config.name}** response: {final_output[:300]}...")
        return {"output": final_output, "tokens": total_tokens, "cost": total_cost, "error": False}


# ─── Multi-Agent Workflow Runner ────────────────────────────────────────────────

class WorkflowRunner:
    """
    Builds and runs a LangGraph StateGraph from a Workflow definition.

    Workflow nodes from the UI are mapped to LangGraph nodes.
    Edges define the message-passing flow between agents.
    Special node types: 'start', 'end', 'condition'.
    """

    def __init__(self, workflow, agents: dict, ws_manager=None, db_session=None):
        self.workflow = workflow
        self.agents = agents          # {agent_id: Agent model}
        self.ws = ws_manager
        self.db = db_session
        self._runners: dict = {}      # {agent_id: AgentRunner}

    def _get_runner(self, agent_id: str) -> AgentRunner:
        if agent_id not in self._runners:
            agent = self.agents[agent_id]
            self._runners[agent_id] = AgentRunner(agent, self.ws, self.db)
        return self._runners[agent_id]

    async def _build_graph(self, execution_id: str):
        nodes = self.workflow.nodes   # [{id, type, data: {agent_id, label}}, ...]
        edges = self.workflow.edges   # [{source, target, ...}]

        # Map node IDs to their agent
        node_agent_map = {}
        special_nodes = set()

        for node in nodes:
            ntype = node.get("type", "agent")
            if ntype in ("start", "end", "trigger"):
                special_nodes.add(node["id"])
            elif ntype == "agent":
                agent_id = node.get("data", {}).get("agent_id")
                if agent_id and agent_id in self.agents:
                    node_agent_map[node["id"]] = agent_id

        # Build adjacency
        adj: dict[str, list[str]] = {}
        for edge in edges:
            src, tgt = edge["source"], edge["target"]
            adj.setdefault(src, []).append(tgt)

        # Determine entry node (connected to 'start' or first in list)
        entry_node = None
        for node in nodes:
            if node.get("type") in ("start", "trigger"):
                targets = adj.get(node["id"], [])
                if targets:
                    entry_node = targets[0]
                break
        if not entry_node and node_agent_map:
            entry_node = list(node_agent_map.keys())[0]

        graph = StateGraph(WorkflowState)

        async def make_agent_node(node_id: str, agent_id: str):
            runner = self._get_runner(agent_id)

            async def node_fn(state: WorkflowState) -> WorkflowState:
                msgs = state.get("messages", [])
                last_human = next(
                    (m.content for m in reversed(msgs) if isinstance(m, HumanMessage)), ""
                )
                result = await runner.run(
                    last_human, state["execution_id"],
                    thread_id=state["execution_id"]
                )
                return {
                    "messages": [AIMessage(content=result["output"],
                                           name=self.agents[agent_id].name)],
                    "current_agent": agent_id,
                    "metadata": {
                        **state.get("metadata", {}),
                        f"{agent_id}_tokens": result["tokens"],
                        f"{agent_id}_cost": result["cost"],
                    },
                }
            return node_fn

        # Add nodes to graph
        for node_id, agent_id in node_agent_map.items():
            graph.add_node(node_id, await make_agent_node(node_id, agent_id))

        # Add edges
        for node_id in node_agent_map:
            if node_id == entry_node:
                graph.add_edge(START, node_id)
            targets = adj.get(node_id, [])
            valid_targets = [t for t in targets if t in node_agent_map]
            if valid_targets:
                for t in valid_targets:
                    graph.add_edge(node_id, t)
            else:
                graph.add_edge(node_id, END)

        if not node_agent_map:
            raise ValueError("Workflow has no valid agent nodes.")

        return graph.compile()

    async def run(self, input_message: str, execution_id: str) -> dict:
        compiled = await self._build_graph(execution_id)
        initial_state: WorkflowState = {
            "messages": [HumanMessage(content=input_message)],
            "current_agent": "",
            "execution_id": execution_id,
            "metadata": {},
        }
        result = await compiled.ainvoke(initial_state)
        msgs = result.get("messages", [])
        final_msg = msgs[-1].content if msgs else ""
        metadata = result.get("metadata", {})
        total_tokens = sum(v for k, v in metadata.items() if k.endswith("_tokens"))
        total_cost = sum(v for k, v in metadata.items() if k.endswith("_cost"))
        return {
            "output": final_msg,
            "tokens": total_tokens,
            "cost": total_cost,
        }
