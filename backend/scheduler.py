"""
Agent & Workflow scheduler powered by APScheduler.

On startup, scans all active agents and workflows for enabled schedules
and registers cron jobs. Jobs fire the agent/workflow exactly as a manual
run would, persisting executions and broadcasting to the Monitor WebSocket.

Agent schedule format  (stored in Agent.schedule JSON):
  {"enabled": true, "cron": "0 9 * * 1-5", "prompt": "Good morning! What's today's news?"}

Workflow trigger format  (stored in Workflow.trigger JSON):
  {"type": "schedule", "cron": "0 8 * * *", "prompt": "Run daily digest."}
"""

import logging
from datetime import datetime
from uuid import uuid4

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


async def start_scheduler(db_factory, ws_manager):
    global _scheduler
    _scheduler = AsyncIOScheduler(timezone="UTC")
    await _register_all_jobs(db_factory, ws_manager)
    _scheduler.start()
    logger.info("✅ Scheduler started.")


def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")


async def _register_all_jobs(db_factory, ws_manager):
    """Load agents and workflows from DB and register enabled cron jobs."""
    from sqlalchemy import select
    from models.agent import Agent
    from models.workflow import Workflow

    async with db_factory() as db:
        agents = (await db.execute(select(Agent).where(Agent.is_active == True))).scalars().all()
        workflows = (await db.execute(select(Workflow).where(Workflow.is_active == True))).scalars().all()

    for agent in agents:
        sched = agent.schedule or {}
        if sched.get("enabled") and sched.get("cron"):
            _register_agent_job(agent.id, sched["cron"], sched.get("prompt", "Run scheduled task."),
                                db_factory, ws_manager)

    for wf in workflows:
        trigger = wf.trigger or {}
        if trigger.get("type") == "schedule" and trigger.get("cron"):
            _register_workflow_job(wf.id, trigger["cron"], trigger.get("prompt", "Run scheduled workflow."),
                                   db_factory, ws_manager)


def _register_agent_job(agent_id: str, cron: str, prompt: str, db_factory, ws_manager):
    try:
        _scheduler.add_job(
            _run_agent,
            trigger=CronTrigger.from_crontab(cron, timezone="UTC"),
            args=[agent_id, prompt, db_factory, ws_manager],
            id=f"agent_{agent_id}",
            replace_existing=True,
            misfire_grace_time=60,
        )
        logger.info(f"Scheduled agent {agent_id} → cron '{cron}'")
    except Exception as e:
        logger.warning(f"Could not schedule agent {agent_id}: {e}")


def _register_workflow_job(workflow_id: str, cron: str, prompt: str, db_factory, ws_manager):
    try:
        _scheduler.add_job(
            _run_workflow,
            trigger=CronTrigger.from_crontab(cron, timezone="UTC"),
            args=[workflow_id, prompt, db_factory, ws_manager],
            id=f"workflow_{workflow_id}",
            replace_existing=True,
            misfire_grace_time=60,
        )
        logger.info(f"Scheduled workflow {workflow_id} → cron '{cron}'")
    except Exception as e:
        logger.warning(f"Could not schedule workflow {workflow_id}: {e}")


async def _run_agent(agent_id: str, prompt: str, db_factory, ws_manager):
    """Fire a scheduled single-agent run."""
    from models.agent import Agent
    from models.execution import Execution, ExecutionLog
    from runtime.engine import AgentRunner

    logger.info(f"Scheduler firing agent {agent_id}")
    try:
        async with db_factory() as db:
            agent = await db.get(Agent, agent_id)
            if not agent or not agent.is_active:
                return

            execution = Execution(
                agent_id=agent_id,
                input_message=prompt,
                status="running",
                trigger_type="schedule",
            )
            db.add(execution)
            await db.commit()
            await db.refresh(execution)

        runner = AgentRunner(agent, ws_manager, db_factory=db_factory)
        result = await runner.run(prompt, execution.id, thread_id=f"schedule_{agent_id}")

        async with db_factory() as db:
            execution = await db.get(Execution, execution.id)
            execution.status = "failed" if result["error"] else "completed"
            execution.output_message = result["output"]
            execution.total_tokens = result["tokens"]
            execution.total_cost = result["cost"]
            execution.completed_at = datetime.utcnow()
            db.add(ExecutionLog(
                execution_id=execution.id,
                agent_id=agent_id,
                agent_name=agent.name,
                log_type="message",
                content=result["output"],
                extra_data={"tokens": result["tokens"], "cost": result["cost"]},
            ))
            await db.commit()

    except Exception as e:
        logger.exception(f"Scheduled agent run failed for {agent_id}: {e}")


async def _run_workflow(workflow_id: str, prompt: str, db_factory, ws_manager):
    """Fire a scheduled workflow run."""
    from sqlalchemy import select
    from models.workflow import Workflow
    from models.agent import Agent
    from models.execution import Execution, ExecutionLog
    from runtime.engine import WorkflowRunner

    logger.info(f"Scheduler firing workflow {workflow_id}")
    try:
        async with db_factory() as db:
            wf = await db.get(Workflow, workflow_id)
            if not wf or not wf.is_active:
                return

            agent_ids = [
                node["data"]["agent_id"]
                for node in wf.nodes
                if node.get("type") == "agent" and node.get("data", {}).get("agent_id")
            ]
            agents_map = {}
            for aid in agent_ids:
                a = await db.get(Agent, aid)
                if a:
                    agents_map[aid] = a

            if not agents_map:
                return

            execution = Execution(
                workflow_id=workflow_id,
                input_message=prompt,
                status="running",
                trigger_type="schedule",
            )
            db.add(execution)
            await db.commit()
            await db.refresh(execution)

        runner = WorkflowRunner(wf, agents_map, ws_manager, db_factory=db_factory)
        result = await runner.run(prompt, execution.id)

        async with db_factory() as db:
            execution = await db.get(Execution, execution.id)
            execution.status = "completed"
            execution.output_message = result["output"]
            execution.total_tokens = result["tokens"]
            execution.total_cost = result["cost"]
            execution.completed_at = datetime.utcnow()
            db.add(ExecutionLog(
                execution_id=execution.id,
                log_type="message",
                content=result["output"],
                extra_data={"tokens": result["tokens"], "cost": result["cost"]},
            ))
            await db.commit()

    except Exception as e:
        logger.exception(f"Scheduled workflow run failed for {workflow_id}: {e}")
