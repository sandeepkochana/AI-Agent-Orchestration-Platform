"""
LangGraph-based agent runtime engine.

Architecture:
- Single-agent: uses create_react_agent with a ToolNode to handle tool calls.
- Multi-agent workflow: builds a StateGraph where each node is an agent.
  Agents communicate via the shared graph state (async message passing).
  Edges are derived from the workflow definition (nodes + edges from the UI).

Features:
- Guardrails: banned topic pre-check, max_token budget post-check.
- Persistent memory: loads/saves conversation per thread_id via ThreadMessage.
"""

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
    "gpt-4o":       {"input": 5e-6,    "output": 15e-6},
    "gpt-4o-mini":  {"input": 0.15e-6, "output": 0.6e-6},
    "gpt-4-turbo":  {"input": 10e-6,   "output": 30e-6},
    "gpt-3.5-turbo":{"input": 0.5e-6,  "output": 1.5e-6},
}

def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    rates = COST_PER_TOKEN.get(model, {"input": 1e-6, "output": 2e-6})
    return input_tokens * rates["input"] + output_tokens * rates["output"]


# ─── Single-Agent Runner ────────────────────────────────────────────────────────

class AgentRunner:
    """
    Wraps a single agent (LangGraph ReAct) with:
    - Guardrails: banned-topic pre-check, token-budget post-check
    - Persistent memory: load/save ThreadMessage rows per thread_id
    - WebSocket logging
    """

    def __init__(self, agent_config, ws_manager=None, db_session=None, db_factory=None):
        self.config = agent_config
        self.ws = ws_manager
        self.db = db_session          # used by callers for execution tracking
        self.db_factory = db_factory  # used internally for memory

        self.llm = ChatOpenAI(
            model=agent_config.model,
            temperature=agent_config.temperature,
            api_key=settings.OPENAI_API_KEY,
            model_kwargs={"stream_options": {"include_usage": True}},
        )
        self.tools = get_tools_for_agent(agent_config.tools or [])
        self.graph = create_react_agent(
            self.llm,
            self.tools,
            state_modifier=agent_config.system_prompt,
        )

    # ── Emit ──────────────────────────────────────────────────────────────────

    async def _emit(self, execution_id: str, log_type: str, content: str, meta: dict = None):
        if self.ws:
            await self.ws.send_log(execution_id, self.config.name, log_type, content, meta)

    # ── Memory ────────────────────────────────────────────────────────────────

    async def _load_history(self, thread_id: str) -> list:
        """Return the last 20 messages for this thread from the DB."""
        if not self.db_factory or not getattr(self.config, "memory_enabled", False):
            return []
        try:
            from models.thread_message import ThreadMessage
            from sqlalchemy import select
            async with self.db_factory() as db:
                result = await db.execute(
                    select(ThreadMessage)
                    .where(ThreadMessage.thread_id == thread_id)
                    .order_by(ThreadMessage.timestamp)
                    .limit(20)
                )
                rows = result.scalars().all()
            msgs = []
            for r in rows:
                if r.role == "human":
                    msgs.append(HumanMessage(content=r.content))
                else:
                    msgs.append(AIMessage(content=r.content))
            return msgs
        except Exception as e:
            logger.warning(f"Memory load failed: {e}")
            return []

    async def _save_messages(self, thread_id: str, human_msg: str, ai_msg: str):
        """Persist the latest exchange to the DB."""
        if not self.db_factory or not getattr(self.config, "memory_enabled", False):
            return
        try:
            from models.thread_message import ThreadMessage
            async with self.db_factory() as db:
                db.add(ThreadMessage(
                    thread_id=thread_id,
                    agent_id=getattr(self.config, "id", None),
                    role="human",
                    content=human_msg,
                ))
                db.add(ThreadMessage(
                    thread_id=thread_id,
                    agent_id=getattr(self.config, "id", None),
                    role="ai",
                    content=ai_msg,
                ))
                await db.commit()
        except Exception as e:
            logger.warning(f"Memory save failed: {e}")

    # ── Guardrails ────────────────────────────────────────────────────────────

    def _check_banned_topics(self, message: str) -> Optional[str]:
        """Returns a refusal string if the message matches a banned topic, else None."""
        guardrails = getattr(self.config, "guardrails", {}) or {}
        banned = guardrails.get("banned_topics", [])
        lower = message.lower()
        for topic in banned:
            if topic.lower() in lower:
                return f"I'm not able to discuss that topic ({topic})."
        return None

    def _check_token_budget(self, total_tokens: int) -> Optional[str]:
        """Returns an error string if the token budget is exceeded, else None."""
        guardrails = getattr(self.config, "guardrails", {}) or {}
        max_tokens = guardrails.get("max_tokens")
        if max_tokens and total_tokens > int(max_tokens):
            return f"Response stopped: token budget ({max_tokens}) exceeded."
        return None

    # ── Run ───────────────────────────────────────────────────────────────────

    async def run(
        self,
        message: str,
        execution_id: str,
        thread_id: Optional[str] = None,
        history: list = None,
    ) -> dict:
        thread_id = thread_id or str(uuid4())

        # ── Guardrail: banned topics ──────────────────────────────────────────
        refusal = self._check_banned_topics(message)
        if refusal:
            await self._emit(execution_id, "error",
                             f"🚫 Guardrail blocked message: {refusal}")
            return {"output": refusal, "tokens": 0, "cost": 0.0, "error": False}

        # ── Memory: load history ──────────────────────────────────────────────
        if history is None:
            history = await self._load_history(thread_id)

        cfg = {"configurable": {"thread_id": thread_id}}
        messages = history + [HumanMessage(content=message)]

        total_tokens = 0
        total_cost = 0.0
        final_output = ""

        await self._emit(execution_id, "message",
                         f"▶ Agent **{self.config.name}** processing: {message}")

        try:
            async for event in self.graph.astream_events(
                {"messages": messages}, cfg, version="v1"
            ):
                kind = event["event"]
                name = event.get("name", "")

                if kind == "on_chat_model_stream":
                    chunk = event["data"].get("chunk")
                    if chunk:
                        if chunk.content:
                            final_output += chunk.content
                        # OpenAI sends a final usage-only chunk when
                        # stream_options.include_usage=True
                        meta = getattr(chunk, "usage_metadata", None)
                        if meta:
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
            result = await self.graph.ainvoke(
                {"messages": [HumanMessage(content=message)]}, cfg
            )
            msgs = result.get("messages", [])
            final_output = msgs[-1].content if msgs else ""

        # ── Guardrail: token budget ───────────────────────────────────────────
        budget_err = self._check_token_budget(total_tokens)
        if budget_err:
            await self._emit(execution_id, "error", f"🚫 Guardrail: {budget_err}")
            return {"output": budget_err, "tokens": total_tokens, "cost": total_cost, "error": True}

        await self._emit(execution_id, "message",
                         f"✅ **{self.config.name}** response: {final_output[:300]}...")

        # ── Memory: save exchange ─────────────────────────────────────────────
        if final_output:
            await self._save_messages(thread_id, message, final_output)

        return {"output": final_output, "tokens": total_tokens, "cost": total_cost, "error": False}


# ─── Multi-Agent Workflow Runner ────────────────────────────────────────────────

class WorkflowRunner:
    """
    Builds and runs a LangGraph StateGraph from a Workflow definition.

    Workflow nodes from the UI are mapped to LangGraph nodes.
    Edges define the message-passing flow between agents.
    Special node types: 'start', 'end', 'condition'.
    """

    def __init__(self, workflow, agents: dict, ws_manager=None, db_session=None, db_factory=None):
        self.workflow = workflow
        self.agents = agents          # {agent_id: Agent model}
        self.ws = ws_manager
        self.db = db_session
        self.db_factory = db_factory
        self._runners: dict = {}      # {agent_id: AgentRunner}

    def _get_runner(self, agent_id: str) -> AgentRunner:
        if agent_id not in self._runners:
            agent = self.agents[agent_id]
            self._runners[agent_id] = AgentRunner(
                agent, self.ws, self.db, db_factory=self.db_factory
            )
        return self._runners[agent_id]

    async def _build_graph(self, execution_id: str):
        nodes = self.workflow.nodes   # [{id, type, data: {agent_id, label}}, ...]
        edges = self.workflow.edges   # [{source, target, ...}]

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

        adj: dict[str, list[str]] = {}
        for edge in edges:
            src, tgt = edge["source"], edge["target"]
            adj.setdefault(src, []).append(tgt)

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
            agent_name = self.agents[agent_id].name

            async def node_fn(state: WorkflowState) -> WorkflowState:
                msgs = state.get("messages", [])
                # Use the last message in state as input — this gives each
                # downstream agent the previous agent's output rather than
                # always replaying the original human prompt.
                last_input = msgs[-1].content if msgs else ""

                result = await runner.run(
                    last_input, state["execution_id"],
                    thread_id=state["execution_id"]
                )

                # Persist a per-step execution log so the Monitor and metrics
                # can see individual agent contributions.
                if self.db_factory:
                    try:
                        from models.execution import ExecutionLog
                        async with self.db_factory() as db:
                            db.add(ExecutionLog(
                                execution_id=state["execution_id"],
                                agent_id=agent_id,
                                agent_name=agent_name,
                                log_type="message",
                                content=result["output"],
                                extra_data={
                                    "tokens": result["tokens"],
                                    "cost":   result["cost"],
                                },
                            ))
                            await db.commit()
                    except Exception as e:
                        logger.warning(f"Failed to persist workflow step log: {e}")

                return {
                    "messages": [AIMessage(content=result["output"], name=agent_name)],
                    "current_agent": agent_id,
                    "metadata": {
                        **state.get("metadata", {}),
                        f"{agent_id}_tokens": result["tokens"],
                        f"{agent_id}_cost":   result["cost"],
                    },
                }
            return node_fn

        for node_id, agent_id in node_agent_map.items():
            graph.add_node(node_id, await make_agent_node(node_id, agent_id))

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
            "cost":   total_cost,
        }
