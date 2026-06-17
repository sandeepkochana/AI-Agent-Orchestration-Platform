import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import init_db, AsyncSessionLocal
from api import agents_router, workflows_router, exec_router, msg_router
from websocket.manager import ws_manager

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
logger = logging.getLogger(__name__)

_telegram_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────────
    logger.info("Initialising database …")
    await init_db()

    if settings.TELEGRAM_BOT_TOKEN:
        logger.info("Starting Telegram bot …")
        await _start_telegram()

    if settings.SLACK_BOT_TOKEN and settings.SLACK_APP_TOKEN:
        logger.info("Starting Slack bot …")
        await _start_slack()

    logger.info("Starting scheduler …")
    from scheduler import start_scheduler
    await start_scheduler(AsyncSessionLocal, ws_manager)

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────────
    if _telegram_task:
        _telegram_task.cancel()
        try:
            await _telegram_task
        except asyncio.CancelledError:
            pass
        from channels.telegram import stop_telegram_bot
        await stop_telegram_bot()

    if settings.SLACK_BOT_TOKEN:
        from channels.slack import stop_slack_bot
        await stop_slack_bot()

    from scheduler import stop_scheduler
    stop_scheduler()


async def _start_telegram():
    """Boot the Telegram bot with the first agent that has the 'telegram' channel."""
    from sqlalchemy import select
    from models.agent import Agent
    from channels.telegram import start_telegram_bot
    from runtime.engine import AgentRunner

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Agent).where(Agent.is_active == True)
        )
        agents = result.scalars().all()
        telegram_agent = next(
            (a for a in agents if "telegram" in (a.channels or [])), None
        )

    if not telegram_agent:
        logger.warning("No agent with 'telegram' channel configured. Telegram bot not started.")
        return

    runner = AgentRunner(telegram_agent, ws_manager, db_factory=AsyncSessionLocal)
    await start_telegram_bot(
        settings.TELEGRAM_BOT_TOKEN,
        runner,
        AsyncSessionLocal,
        ws_manager,
    )


async def _start_slack():
    """Boot the Slack bot with the first agent that has the 'slack' channel."""
    from sqlalchemy import select
    from models.agent import Agent
    from channels.slack import start_slack_bot
    from runtime.engine import AgentRunner

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Agent).where(Agent.is_active == True)
        )
        agents = result.scalars().all()
        slack_agent = next(
            (a for a in agents if "slack" in (a.channels or [])), None
        )

    if not slack_agent:
        logger.warning("No agent with 'slack' channel configured. Slack bot not started.")
        return

    runner = AgentRunner(slack_agent, ws_manager, db_factory=AsyncSessionLocal)
    await start_slack_bot(
        settings.SLACK_BOT_TOKEN,
        settings.SLACK_APP_TOKEN,
        runner,
        AsyncSessionLocal,
        ws_manager,
    )


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── REST routes ──────────────────────────────────────────────────────────────
app.include_router(agents_router, prefix="/api")
app.include_router(workflows_router, prefix="/api")
app.include_router(exec_router, prefix="/api")
app.include_router(msg_router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME}


# ── WebSocket ────────────────────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket, "global")
    try:
        while True:
            await websocket.receive_text()   # keep alive
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, "global")


@app.websocket("/ws/{execution_id}")
async def websocket_execution(websocket: WebSocket, execution_id: str):
    await ws_manager.connect(websocket, execution_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, execution_id)
