from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from database import get_db
from models.workflow import Workflow
from models.agent import Agent
from models.execution import Execution, ExecutionLog
from schemas import WorkflowCreate, WorkflowUpdate, WorkflowResponse, RunWorkflowRequest
from runtime.engine import WorkflowRunner
from websocket.manager import ws_manager
from templates.workflows import TEMPLATES

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.get("/", response_model=list[WorkflowResponse])
async def list_workflows(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Workflow).order_by(Workflow.created_at.desc()))
    return result.scalars().all()


@router.post("/", response_model=WorkflowResponse, status_code=201)
async def create_workflow(payload: WorkflowCreate, db: AsyncSession = Depends(get_db)):
    wf = Workflow(**payload.model_dump())
    db.add(wf)
    await db.commit()
    await db.refresh(wf)
    return wf


@router.get("/templates")
async def list_templates():
    return TEMPLATES


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(workflow_id: str, db: AsyncSession = Depends(get_db)):
    wf = await db.get(Workflow, workflow_id)
    if not wf:
        raise HTTPException(404, "Workflow not found")
    return wf


@router.put("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(workflow_id: str, payload: WorkflowUpdate, db: AsyncSession = Depends(get_db)):
    wf = await db.get(Workflow, workflow_id)
    if not wf:
        raise HTTPException(404, "Workflow not found")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(wf, k, v)
    await db.commit()
    await db.refresh(wf)
    return wf


@router.delete("/{workflow_id}", status_code=204)
async def delete_workflow(workflow_id: str, db: AsyncSession = Depends(get_db)):
    wf = await db.get(Workflow, workflow_id)
    if not wf:
        raise HTTPException(404, "Workflow not found")
    await db.delete(wf)
    await db.commit()


@router.post("/{workflow_id}/run")
async def run_workflow(workflow_id: str, payload: RunWorkflowRequest, db: AsyncSession = Depends(get_db)):
    wf = await db.get(Workflow, workflow_id)
    if not wf:
        raise HTTPException(404, "Workflow not found")

    # Gather all agents referenced in workflow nodes
    agent_ids = [
        node["data"]["agent_id"]
        for node in wf.nodes
        if node.get("type") == "agent" and node.get("data", {}).get("agent_id")
    ]

    agents_map = {}
    for aid in agent_ids:
        agent = await db.get(Agent, aid)
        if agent:
            agents_map[aid] = agent

    if not agents_map:
        raise HTTPException(422, "Workflow has no valid agent nodes with matching agents.")

    execution = Execution(
        workflow_id=workflow_id,
        input_message=payload.input_message,
        status="running",
        trigger_type=payload.trigger_type,
    )
    db.add(execution)
    await db.commit()
    await db.refresh(execution)

    await ws_manager.send_status(execution.id, "running")

    runner = WorkflowRunner(wf, agents_map, ws_manager, db)
    try:
        result = await runner.run(payload.input_message, execution.id)
        execution.status = "completed"
        execution.output_message = result["output"]
        execution.total_tokens = result["tokens"]
        execution.total_cost = result["cost"]
    except Exception as e:
        execution.status = "failed"
        execution.output_message = str(e)

    execution.completed_at = datetime.utcnow()
    await db.commit()

    log = ExecutionLog(
        execution_id=execution.id,
        log_type="message",
        content=execution.output_message,
        metadata={"tokens": execution.total_tokens, "cost": execution.total_cost},
    )
    db.add(log)
    await db.commit()

    await ws_manager.send_status(execution.id, execution.status,
                                  {"output": execution.output_message})

    return {
        "execution_id": execution.id,
        "output": execution.output_message,
        "status": execution.status,
        "tokens": execution.total_tokens,
        "cost": execution.total_cost,
    }
