"""
Tests for critical paths: agent creation, workflow execution, message delivery.
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
    assert len(TEMPLATES) >= 2
    for t in TEMPLATES:
        assert "name" in t
        assert "nodes" in t
        assert "edges" in t


def test_workflow_template_structure():
    from templates.workflows import TEMPLATES
    t = TEMPLATES[0]
    node_ids = {n["id"] for n in t["nodes"]}
    for edge in t["edges"]:
        assert edge["source"] in node_ids
        assert edge["target"] in node_ids


# ─── Config ──────────────────────────────────────────────────────────────────

def test_config_loads():
    from config import settings
    assert settings.APP_NAME
    assert settings.DEFAULT_MODEL
