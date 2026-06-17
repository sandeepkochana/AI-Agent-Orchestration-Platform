from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db, AsyncSessionLocal
from models.agent import Agent
from schemas import AgentCreate, AgentUpdate, AgentResponse, RunAgentRequest
from runtime.tools import AVAILABLE_TOOLS
from runtime.engine import AgentRunner
from websocket.manager import ws_manager

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/", response_model=list[AgentResponse])
async def list_agents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).order_by(Agent.created_at.desc()))
    return result.scalars().all()


@router.post("/", response_model=AgentResponse, status_code=201)
async def create_agent(payload: AgentCreate, db: AsyncSession = Depends(get_db)):
    agent = Agent(**payload.model_dump())
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent


@router.get("/tools", response_model=list[str])
async def list_available_tools():
    return AVAILABLE_TOOLS


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(404, "Agent not found")
    return agent


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(agent_id: str, payload: AgentUpdate, db: AsyncSession = Depends(get_db)):
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(404, "Agent not found")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(agent, k, v)
    await db.commit()
    await db.refresh(agent)
    return agent


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(404, "Agent not found")
    await db.delete(agent)
    await db.commit()


@router.post("/{agent_id}/run")
async def run_agent(agent_id: str, payload: RunAgentRequest, db: AsyncSession = Depends(get_db)):
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(404, "Agent not found")

    from models.execution import Execution, ExecutionLog
    from datetime import datetime

    execution = Execution(
        agent_id=agent_id,
        input_message=payload.message,
        status="running",
        trigger_type="manual",
    )
    db.add(execution)
    await db.commit()
    await db.refresh(execution)

    await ws_manager.send_status(execution.id, "running")

    runner = AgentRunner(agent, ws_manager, db, db_factory=AsyncSessionLocal)
    result = await runner.run(payload.message, execution.id, thread_id=payload.thread_id)

    execution.status = "failed" if result["error"] else "completed"
    execution.output_message = result["output"]
    execution.total_tokens = result["tokens"]
    execution.total_cost = result["cost"]
    execution.completed_at = datetime.utcnow()
    await db.commit()

    # Persist final log
    log = ExecutionLog(
        execution_id=execution.id,
        agent_id=agent_id,
        agent_name=agent.name,
        log_type="message",
        content=result["output"],
        extra_data={"tokens": result["tokens"], "cost": result["cost"]},
    )
    db.add(log)
    await db.commit()

    await ws_manager.send_status(execution.id, execution.status,
                                  {"output": result["output"], "tokens": result["tokens"],
                                   "cost": result["cost"]})

    return {
        "execution_id": execution.id,
        "output": result["output"],
        "tokens": result["tokens"],
        "cost": result["cost"],
        "status": execution.status,
    }
