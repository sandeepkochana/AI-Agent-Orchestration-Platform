# AI Agent Orchestration Platform

A full-stack platform to create, configure, and orchestrate collaborative AI agents — with a visual workflow builder, real-time monitoring, and Telegram channel integration.

---

## Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Browser (React + Vite)                          │
│                                                                        │
│   Dashboard │ Agents CRUD │ Workflow Builder │ Monitor │ Messages      │
│               (ReactFlow canvas w/ condition nodes)  (WS live feed)   │
└───────────────────────────┬────────────────────────────────────────────┘
                            │ HTTP REST + WebSocket
┌───────────────────────────▼────────────────────────────────────────────┐
│                     FastAPI Backend (Python)                           │
│                                                                        │
│   /api/agents     /api/workflows     /api/executions     /api/messages │
│   /ws  (WebSocket broadcast hub)                                       │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    LangGraph Runtime Engine                       │  │
│  │                                                                  │  │
│  │  Single Agent: create_react_agent(LLM, tools)                    │  │
│  │  + interaction_rules injected into system prompt                 │  │
│  │                                                                  │  │
│  │  Multi-Agent Workflow (StateGraph):                              │  │
│  │  START ──► AgentNode ──► ConditionNode ──► AgentNode ──► END    │  │
│  │                    ↑____________(false/loop)                     │  │
│  │                                                                  │  │
│  │  Condition nodes: LLM evaluates boolean → routes true/false      │  │
│  │  Feedback loops: bounded by iteration_count + recursion_limit    │  │
│  │  Tools: web_search │ calculator │ http_request │ get_datetime    │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  ┌────────────┐  │
│  │ Telegram Bot │  │  Slack Bot   │  │  WS Mgr    │  │  SQLite    │  │
│  │ (ptb v21)    │  │ (slack-bolt) │  │ broadcasts │  │ async ORM  │  │
│  └──────────────┘  └──────────────┘  └────────────┘  └────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
          │                    │
    Telegram API           Slack API
   (external channels)
```

---

## Tech Stack & Justification

| Layer | Choice | Why |
|---|---|---|
| **AI Framework** | **LangGraph** | Best for multi-agent graphs with explicit state passing. Unlike CrewAI/AutoGen, LangGraph gives you full control over the graph topology — edges, conditions, and feedback loops. `create_react_agent` handles single-agent ReAct loops cleanly, while `StateGraph` handles multi-agent coordination. |
| **Backend** | **FastAPI (Python)** | Native async, automatic OpenAPI docs, and first-class support for the entire LangChain/LangGraph ecosystem. Streaming agent responses via `astream_events` integrates naturally. |
| **Database** | **SQLite + SQLAlchemy async** | Zero-config local persistence. Swap to PostgreSQL by changing `DATABASE_URL` — no code changes needed. |
| **Frontend** | **React + Vite + TypeScript** | Fast DX, small bundle. Vite proxy keeps CORS simple in dev. |
| **Workflow UI** | **ReactFlow (@xyflow/react)** | Purpose-built for node-edge graph editors. Handles drag, connect, minimap, and zoom out of the box. |
| **Messaging** | **Telegram + Slack** | Telegram needs only a bot token from @BotFather. Slack uses Socket Mode (no public webhook needed) — both start automatically if their tokens are in `.env`. |
| **Real-time** | **WebSocket (native FastAPI)** | One `/ws` endpoint broadcasts all agent events (logs, tool calls, status) to the UI live. |

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- An OpenAI API key
- (Optional) A Telegram bot token from [@BotFather](https://t.me/BotFather)

### 1 — Clone & setup

```bash
git clone https://github.com/sandeepkochana/AI-Agent-Orchestration-Platform.git
cd AI-Agent-Orchestration-Platform
bash setup.sh
```

This installs all Python and Node dependencies and creates `backend/.env` from the example.

### 2 — Configure

Edit `backend/.env`:

```env
OPENAI_API_KEY=sk-...
TELEGRAM_BOT_TOKEN=      # optional — paste your bot token here
```

### 3 — Seed demo data (optional but recommended)

```bash
cd backend
source .venv/bin/activate
python seed.py
```

Creates a **Researcher** agent, a **Writer** agent, a **Research → Write** workflow, and a **Quality Review Loop** workflow (demonstrates condition nodes + feedback loops). Safe to re-run — skips anything that already exists.

### 4 — Start

**Terminal 1 — Backend:**
```bash
cd backend
source .venv/bin/activate
uvicorn main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```

Open **http://localhost:3000** (or the port Vite reports if 3000 is taken)

---

## Features

### Agent CRUD
Create agents with:
- **Name, Role, System Prompt** — personality and purpose
- **Model** — `gpt-4o-mini`, `gpt-4o`, `gpt-4-turbo`, `gpt-3.5-turbo`
- **Tools** — `web_search`, `calculator`, `http_request`, `get_current_datetime`
- **Channels** — `telegram`, `slack`
- **Memory toggle** — persistent conversation history per thread
- **Max iterations, temperature** — runtime controls
- **Guardrails** — banned topic pre-check, token budget post-check
- **Schedule** — cron + auto-run prompt (APScheduler)
- **Interaction Rules** — response format (plain/markdown/JSON), tone (professional/casual/concise/detailed), custom instructions; all injected into the system prompt at runtime

### Visual Workflow Builder
- Drag agents from the sidebar onto the ReactFlow canvas
- Connect nodes by drawing edges (including back-edges for loops)
- **Condition nodes** (⬥) for branching and feedback loops:
  - The LLM evaluates a boolean condition against the previous agent's output
  - Green handle (T) routes to the "pass" branch; red handle (F) routes to the "retry/loop" branch
  - Feedback loops terminate after 5 iterations (soft limit) or 25 node executions (hard cap)
- Start / End sentinel nodes included
- Save to database; run directly from the toolbar
- **2 pre-built templates**: Research & Summarise, Customer Support Triage

### Multi-Agent Execution (LangGraph)
Workflows run as a `StateGraph` where each agent node is a full ReAct agent. Agents pass results downstream via the shared `WorkflowState.messages` list — true async message passing. Condition nodes use `add_conditional_edges` with an LLM-evaluated router.

### Real-time Monitoring
- WebSocket live feed on the Monitor page
- Per-execution step logs (tool calls, tool results, errors, responses)
- Token count + estimated USD cost per run
- Execution history with status indicators

### Telegram Integration
Configure an agent with `channels: ["telegram"]` and set `TELEGRAM_BOT_TOKEN` in `.env`. The bot starts automatically on server boot, routes inbound messages to that agent, and replies in-chat. All messages are persisted and visible on the Messages page.

---

## Adding a New Messaging Channel

1. Create `backend/channels/your_channel.py` — implement `start_your_bot(token, agent_runner, db_factory, ws_manager)` following the pattern in `channels/telegram.py`.
2. Add the channel name to `CHANNELS_OPTIONS` in `frontend/src/components/AgentForm.tsx`.
3. In `backend/main.py`, add a matching `if settings.YOUR_TOKEN:` block in `_start_telegram` (or create a parallel `_start_your_channel` function).

## Adding a New Workflow Template

1. Open `backend/templates/workflows.py`.
2. Append a new dict to the `TEMPLATES` list following the existing schema (`name`, `description`, `nodes`, `edges`, `trigger`).
3. The new template appears immediately in the Workflow Builder UI — no restart needed.

## Adding a New Tool

1. Decorate a function with `@tool` in `backend/runtime/tools.py`.
2. Add it to `TOOL_REGISTRY`.
3. It will appear automatically in the Agent Form tool picker.

---

## Running Tests

```bash
cd backend
source .venv/bin/activate
pytest tests/ -v
```

24 tests covering: agent schema validation, tool registry, calculator, datetime, WebSocket connect/disconnect/broadcast, workflow templates (including condition node structure), config, guardrail banned-topic blocking, guardrail token budget, interaction rule prompt injection, and condition node routing logic (including force-exit after max iterations).

---

## Project Structure

```
AI-Agent-Orchestration-Platform/
├── setup.sh                    # Single setup command
├── .env.example
├── backend/
│   ├── main.py                 # FastAPI app + lifespan (DB init, Telegram boot)
│   ├── config.py               # Pydantic settings (reads .env)
│   ├── database.py             # Async SQLAlchemy engine + session factory
│   ├── requirements.txt
│   ├── models/                 # SQLAlchemy ORM models
│   │   ├── agent.py            # Agent (name, role, tools, channels, guardrails…)
│   │   ├── workflow.py         # Workflow (nodes, edges as JSON)
│   │   ├── execution.py        # Execution + ExecutionLog
│   │   └── message.py          # Channel messages (inbound + outbound)
│   ├── schemas/                # Pydantic request/response schemas
│   ├── api/
│   │   ├── agents.py           # CRUD + /run endpoint
│   │   ├── workflows.py        # CRUD + /run + /templates endpoints
│   │   └── executions.py       # History + logs + messages
│   ├── runtime/
│   │   ├── engine.py           # LangGraph AgentRunner + WorkflowRunner
│   │   └── tools.py            # web_search, calculator, http_request, datetime
│   ├── channels/
│   │   └── telegram.py         # Telegram bot (python-telegram-bot)
│   ├── templates/
│   │   └── workflows.py        # Pre-built workflow templates
│   ├── websocket/
│   │   └── manager.py          # WebSocket connection manager (broadcast hub)
│   └── tests/
│       └── test_critical_paths.py
└── frontend/
    ├── vite.config.ts          # Proxy: /api → :8000, /ws → ws://:8000
    ├── tailwind.config.js
    └── src/
        ├── App.tsx             # Router + WebSocket init
        ├── api/client.ts       # Typed API client (axios)
        ├── store/useStore.ts   # Zustand state (agents, workflows, live logs)
        ├── components/
        │   ├── Sidebar.tsx
        │   ├── AgentForm.tsx
        │   ├── WorkflowNodes.tsx  # ReactFlow custom node types
        │   └── LogViewer.tsx
        └── pages/
            ├── Dashboard.tsx
            ├── Agents.tsx         # CRUD + inline chat panel
            ├── WorkflowBuilder.tsx # ReactFlow canvas + template loader
            ├── Monitor.tsx        # Live feed + execution history
            └── Messages.tsx       # Channel message history
```

---

## End-to-End Demo Flow

Run `python seed.py` first to create the demo agents and workflows, then:

### Demo A — 2-agent pipeline (Research → Write)
1. Open **Workflow Builder** → select **Research → Write**
2. Type *"Latest advancements in LLM fine-tuning 2025"* in the input field → **Run**
3. Watch the **Monitor** live feed — tool calls, inter-agent messages, per-agent token counts

### Demo B — Feedback loop (Quality Review Loop)
1. Open **Workflow Builder** → select **Quality Review Loop**
2. Type any question (e.g. *"What is a transformer model?"*) → **Run**
3. The Writer drafts a response; the Condition node asks the LLM *"Is this ≥ 3 sentences and well-structured?"*
4. If `false` → loops back to Writer (up to 5 times); if `true` → exits to End
5. Monitor shows the `🔀 Condition → true/false` routing event for each iteration

### Demo C — Guardrails
1. Edit any agent → add `politics` to **Banned Topics**
2. Run the agent with a message containing "politics"
3. The response is blocked instantly — the LLM is never called

### Demo D — Telegram channel
Set `TELEGRAM_BOT_TOKEN` in `.env`, create an agent with `channels: ["telegram"]`, restart the backend, message the bot on Telegram.

---

## License

MIT
