from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from database import get_db
from models.execution import Execution, ExecutionLog
from models.message import Message
from schemas import ExecutionResponse, ExecutionLogResponse, MessageResponse

exec_router = APIRouter(prefix="/executions", tags=["executions"])
msg_router = APIRouter(prefix="/messages", tags=["messages"])


@exec_router.get("/", response_model=list[ExecutionResponse])
async def list_executions(
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Execution).order_by(desc(Execution.started_at)).limit(limit)
    )
    return result.scalars().all()


@exec_router.get("/{execution_id}", response_model=ExecutionResponse)
async def get_execution(execution_id: str, db: AsyncSession = Depends(get_db)):
    e = await db.get(Execution, execution_id)
    if not e:
        from fastapi import HTTPException
        raise HTTPException(404, "Execution not found")
    return e


@exec_router.get("/{execution_id}/logs", response_model=list[ExecutionLogResponse])
async def get_execution_logs(execution_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ExecutionLog)
        .where(ExecutionLog.execution_id == execution_id)
        .order_by(ExecutionLog.timestamp)
    )
    return result.scalars().all()


@msg_router.get("/", response_model=list[MessageResponse])
async def list_messages(
    channel: str = Query(None),
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db)
):
    q = select(Message).order_by(desc(Message.created_at)).limit(limit)
    if channel:
        q = q.where(Message.channel == channel)
    result = await db.execute(q)
    return result.scalars().all()
