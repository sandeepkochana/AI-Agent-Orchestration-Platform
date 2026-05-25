"""
Seed script — creates demo agents and workflows for a fresh database.

Run from the backend directory with the virtual environment active:
    python seed.py

Safe to re-run: skips any entity that already exists by name.
"""

import asyncio
from sqlalchemy import select, func

from database import init_db, AsyncSessionLocal
from models.agent import Agent
from models.workflow import Workflow


RESEARCHER_PROMPT = (
    "You are a thorough research assistant. Search the web to gather relevant, "
    "accurate information on the given topic. Summarise your findings clearly."
)
WRITER_PROMPT = (
    "You are a skilled content writer. Take the research findings provided and "
    "craft a clear, engaging, well-structured summary in at least 3 sentences."
)


async def get_or_create_agent(db, name: str, **kwargs) -> Agent:
    result = await db.execute(select(Agent).where(Agent.name == name).limit(1))
    agent = result.scalars().first()
    if agent:
        print(f"  ℹ  Agent already exists: {name} ({agent.id[:8]}…)")
        return agent
    agent = Agent(name=name, **kwargs)
    db.add(agent)
    await db.flush()   # get the generated id
    print(f"  ✅ Created agent:  {name} ({agent.id[:8]}…)")
    return agent


async def get_or_create_workflow(db, name: str, **kwargs) -> Workflow:
    result = await db.execute(select(Workflow).where(Workflow.name == name).limit(1))
    wf = result.scalars().first()
    if wf:
        print(f"  ℹ  Workflow already exists: {name} ({wf.id[:8]}…)")
        return wf
    wf = Workflow(name=name, **kwargs)
    db.add(wf)
    await db.flush()
    print(f"  ✅ Created workflow: {name} ({wf.id[:8]}…)")
    return wf


async def seed():
    print("🌱 Running seed …")
    await init_db()

    async with AsyncSessionLocal() as db:
        # ── Agents ───────────────────────────────────────────────────────────
        print("\n── Agents ───────────────────────────────────────────────")
        researcher = await get_or_create_agent(db, "Researcher",
            role="researcher",
            system_prompt=RESEARCHER_PROMPT,
            model="gpt-4o-mini",
            tools=["web_search", "get_current_datetime"],
            memory_enabled=True,
        )
        writer = await get_or_create_agent(db, "Writer",
            role="writer",
            system_prompt=WRITER_PROMPT,
            model="gpt-4o-mini",
            tools=[],
            memory_enabled=False,
            interaction_rules={"response_format": "markdown", "tone": "professional"},
        )

        # ── Workflows ─────────────────────────────────────────────────────────
        print("\n── Workflows ────────────────────────────────────────────")

        await get_or_create_workflow(db, "Research → Write",
            description="Researcher searches the web; Writer produces a polished summary.",
            nodes=[
                {"id": "start-1",          "type": "start", "position": {"x": 50,  "y": 200}, "data": {"label": "Start"}},
                {"id": "agent-researcher", "type": "agent", "position": {"x": 270, "y": 200}, "data": {"label": "Researcher", "agent_id": researcher.id, "role": "researcher", "model": "gpt-4o-mini", "tools": ["web_search"]}},
                {"id": "agent-writer",     "type": "agent", "position": {"x": 520, "y": 200}, "data": {"label": "Writer",     "agent_id": writer.id,      "role": "writer",      "model": "gpt-4o-mini", "tools": []}},
                {"id": "end-1",            "type": "end",   "position": {"x": 760, "y": 200}, "data": {"label": "End"}},
            ],
            edges=[
                {"id": "e1", "source": "start-1",          "target": "agent-researcher"},
                {"id": "e2", "source": "agent-researcher",  "target": "agent-writer"},
                {"id": "e3", "source": "agent-writer",      "target": "end-1"},
            ],
            trigger={"type": "manual"},
        )

        await get_or_create_workflow(db, "Quality Review Loop",
            description=(
                "Writer drafts a response; a condition node checks quality "
                "and loops back to the writer if insufficient (max 5 iterations). "
                "Demonstrates feedback loops with condition nodes."
            ),
            nodes=[
                {"id": "start-1",          "type": "start",     "position": {"x": 50,  "y": 200}, "data": {"label": "Start"}},
                {"id": "agent-writer",     "type": "agent",     "position": {"x": 270, "y": 200}, "data": {"label": "Writer", "agent_id": writer.id, "role": "writer", "model": "gpt-4o-mini", "tools": []}},
                {"id": "condition-quality","type": "condition", "position": {"x": 530, "y": 200}, "data": {
                    "label": "Quality Check",
                    "condition_prompt": (
                        "Is this response at least 3 sentences long, well-structured, "
                        "and does it directly answer the question? Answer true or false."
                    ),
                }},
                {"id": "end-1",            "type": "end",       "position": {"x": 760, "y": 120}, "data": {"label": "End"}},
            ],
            edges=[
                {"id": "e1", "source": "start-1",           "target": "agent-writer"},
                {"id": "e2", "source": "agent-writer",       "target": "condition-quality"},
                {"id": "e3", "source": "condition-quality",  "target": "end-1",        "sourceHandle": "true"},
                {"id": "e4", "source": "condition-quality",  "target": "agent-writer", "sourceHandle": "false"},
            ],
            trigger={"type": "manual"},
        )

        await db.commit()

    print("\n🎉 Seed complete.\n")
    print("Next steps:")
    print("  1. Start the backend:  uvicorn main:app --reload --port 8000")
    print("  2. Start the frontend: npm run dev")
    print("  3. Open http://localhost:3000 → Workflow Builder → run 'Quality Review Loop'")


if __name__ == "__main__":
    asyncio.run(seed())
