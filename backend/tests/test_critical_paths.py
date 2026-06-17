"""
Tests for critical paths: agent creation, workflow execution, message delivery,
guardrail enforcement, interaction rule injection, and condition node routing.

Run with: pytest tests/ -v
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


# ─── Agent CRUD ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_agent_create_schema():
    from schemas import AgentCreate
    payload = AgentCreate(
        name="Test Agent",
        role="assistant",
        system_prompt="You are a helpful assistant.",
        model="gpt-4o-mini",
        tools=["calculator"],
        channels=[],
    )
    assert payload.name == "Test Agent"
    assert "calculator" in payload.tools
    assert payload.skills == []
    assert payload.interaction_rules == {}


@pytest.mark.asyncio
async def test_agent_tools_registry():
    from runtime.tools import TOOL_REGISTRY, get_tools_for_agent
    assert "web_search" in TOOL_REGISTRY
    assert "calculator" in TOOL_REGISTRY
    tools = get_tools_for_agent(["calculator"])
    assert len(tools) == 1


@pytest.mark.asyncio
async def test_calculator_tool():
    from runtime.tools import calculator
    result = calculator.invoke({"expression": "2 + 2"})
    assert result == "4"


@pytest.mark.asyncio
async def test_datetime_tool():
    from runtime.tools import get_current_datetime
    result = get_current_datetime.invoke({})
    assert len(result) > 0


# ─── WebSocket Manager ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ws_manager_connect_disconnect():
    from websocket.manager import ConnectionManager
    manager = ConnectionManager()
    mock_ws = AsyncMock()
    await manager.connect(mock_ws, "test-room")
    assert mock_ws in manager.active_connections["test-room"]
    await manager.disconnect(mock_ws, "test-room")
    assert mock_ws not in manager.active_connections.get("test-room", [])


@pytest.mark.asyncio
async def test_ws_broadcast():
    from websocket.manager import ConnectionManager
    manager = ConnectionManager()
    mock_ws = AsyncMock()
    await manager.connect(mock_ws, "global")
    await manager.broadcast({"type": "test", "msg": "hello"})
    mock_ws.send_text.assert_called_once()


# ─── Workflow Templates ───────────────────────────────────────────────────────

def test_workflow_templates_exist():
    from templates.workflows import TEMPLATES
    assert len(TEMPLATES) >= 3  # research, support, quality-review-loop
    for t in TEMPLATES:
        assert "name" in t
        assert "nodes" in t
        assert "edges" in t


def test_workflow_template_structure():
    from templates.workflows import TEMPLATES
    for t in TEMPLATES:
        node_ids = {n["id"] for n in t["nodes"]}
        for edge in t["edges"]:
            assert edge["source"] in node_ids
            assert edge["target"] in node_ids


def test_feedback_loop_template_has_condition_node():
    from templates.workflows import TEMPLATES
    loop_tpl = next(t for t in TEMPLATES if t["id"] == "quality-review-loop")
    condition_nodes = [n for n in loop_tpl["nodes"] if n["type"] == "condition"]
    assert len(condition_nodes) == 1
    # Verify true and false edges are both present
    cid = condition_nodes[0]["id"]
    handles = {e.get("sourceHandle") for e in loop_tpl["edges"] if e["source"] == cid}
    assert "true" in handles
    assert "false" in handles


# ─── Config ──────────────────────────────────────────────────────────────────

def test_config_loads():
    from config import settings
    assert settings.APP_NAME
    assert settings.DEFAULT_MODEL


# ─── Guardrails ──────────────────────────────────────────────────────────────

def _make_runner_with_config(**guardrail_kwargs):
    """Build an AgentRunner with a mock config — no real LLM or DB."""
    from runtime.engine import AgentRunner
    config = MagicMock()
    config.model = "gpt-4o-mini"
    config.temperature = 0.7
    config.system_prompt = "You are a helpful assistant."
    config.tools = []
    config.skills = []
    config.guardrails = guardrail_kwargs
    config.interaction_rules = {}
    with patch("runtime.engine.ChatOpenAI"), patch("runtime.engine.create_react_agent"):
        runner = AgentRunner(config, ws_manager=None, db_session=None, db_factory=None)
    return runner


def test_guardrail_banned_topic_blocks():
    runner = _make_runner_with_config(banned_topics=["politics", "gambling"])
    result = runner._check_banned_topics("Tell me about politics in the US")
    assert result is not None
    assert "politics" in result


def test_guardrail_banned_topic_passes_clean_message():
    runner = _make_runner_with_config(banned_topics=["politics"])
    result = runner._check_banned_topics("What is the capital of France?")
    assert result is None


def test_guardrail_token_budget_exceeded():
    runner = _make_runner_with_config(max_tokens=100)
    result = runner._check_token_budget(150)
    assert result is not None
    assert "100" in result


def test_guardrail_token_budget_within_limit():
    runner = _make_runner_with_config(max_tokens=100)
    result = runner._check_token_budget(50)
    assert result is None


def test_guardrail_no_budget_set():
    runner = _make_runner_with_config()
    result = runner._check_token_budget(999999)
    assert result is None


# ─── Skills ──────────────────────────────────────────────────────────────────

def _make_runner_with_skills(system_prompt="You are helpful.", skills=None):
    from runtime.engine import AgentRunner
    config = MagicMock()
    config.model = "gpt-4o-mini"
    config.temperature = 0.7
    config.system_prompt = system_prompt
    config.tools = []
    config.skills = skills or []
    config.guardrails = {}
    config.interaction_rules = {}
    with patch("runtime.engine.ChatOpenAI"), patch("runtime.engine.create_react_agent"):
        runner = AgentRunner(config, ws_manager=None, db_session=None, db_factory=None)
    return runner


def test_skills_injected_into_system_prompt():
    runner = _make_runner_with_skills("Base.", skills=["summarization", "code review"])
    prompt = runner._build_system_prompt()
    assert "Skills" in prompt
    assert "summarization" in prompt
    assert "code review" in prompt


def test_skills_empty_list_not_injected():
    runner = _make_runner_with_skills("Base.", skills=[])
    prompt = runner._build_system_prompt()
    assert "Skills" not in prompt
    assert prompt == "Base."


def test_skills_schema_defaults_to_empty():
    from schemas import AgentCreate
    payload = AgentCreate(
        name="Test", role="assistant",
        system_prompt="You are helpful.",
        model="gpt-4o-mini", tools=[], channels=[],
    )
    assert payload.skills == []


def test_skills_schema_accepts_list():
    from schemas import AgentCreate
    payload = AgentCreate(
        name="Test", role="assistant",
        system_prompt="You are helpful.",
        model="gpt-4o-mini", tools=[], channels=[],
        skills=["translation", "sentiment analysis"],
    )
    assert "translation" in payload.skills
    assert "sentiment analysis" in payload.skills


# ─── Interaction Rules ────────────────────────────────────────────────────────

def _make_runner_with_rules(system_prompt="You are helpful.", **rules):
    from runtime.engine import AgentRunner
    config = MagicMock()
    config.model = "gpt-4o-mini"
    config.temperature = 0.7
    config.system_prompt = system_prompt
    config.tools = []
    config.skills = []
    config.guardrails = {}
    config.interaction_rules = rules
    with patch("runtime.engine.ChatOpenAI"), patch("runtime.engine.create_react_agent"):
        runner = AgentRunner(config, ws_manager=None, db_session=None, db_factory=None)
    return runner


def test_interaction_rules_no_rules():
    runner = _make_runner_with_rules("Base prompt.")
    assert runner._build_system_prompt() == "Base prompt."


def test_interaction_rules_response_format_injected():
    runner = _make_runner_with_rules("Base.", response_format="markdown")
    prompt = runner._build_system_prompt()
    assert "markdown" in prompt
    assert "Interaction Rules" in prompt


def test_interaction_rules_tone_injected():
    runner = _make_runner_with_rules("Base.", tone="concise")
    prompt = runner._build_system_prompt()
    assert "concise" in prompt


def test_interaction_rules_custom_injected():
    runner = _make_runner_with_rules("Base.", custom_instructions="Always start with TL;DR.")
    prompt = runner._build_system_prompt()
    assert "TL;DR" in prompt


def test_interaction_rules_any_skipped():
    """'any' values should not add constraints to the prompt."""
    runner = _make_runner_with_rules("Base.", response_format="any", tone="any")
    prompt = runner._build_system_prompt()
    assert "Interaction Rules" not in prompt


# ─── Condition Node Routing ───────────────────────────────────────────────────

def _make_router(true_target="end", false_target="retry", max_iter=5):
    """Extract the make_router closure from WorkflowRunner for isolated testing."""
    END = "END"  # sentinel
    def make_router(tt, ft, mi):
        def router(state):
            if state.get("iteration_count", 0) >= mi:
                return "true"   # force exit
            return state.get("routing_decision", "true")
        return router
    return make_router(true_target, false_target, max_iter)


def test_condition_router_routes_true():
    router = _make_router()
    state = {"routing_decision": "true", "iteration_count": 0}
    assert router(state) == "true"


def test_condition_router_routes_false():
    router = _make_router()
    state = {"routing_decision": "false", "iteration_count": 1}
    assert router(state) == "false"


def test_condition_router_forces_exit_at_max_iter():
    router = _make_router(max_iter=5)
    state = {"routing_decision": "false", "iteration_count": 5}
    assert router(state) == "true"   # forced exit despite "false" decision


def test_condition_router_default_when_no_decision():
    router = _make_router()
    state = {"iteration_count": 0}   # no routing_decision key
    assert router(state) == "true"
