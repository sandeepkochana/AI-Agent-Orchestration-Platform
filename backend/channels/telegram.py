"""
Telegram channel integration.

Runs a telegram.ext.Application alongside the FastAPI server.
Inbound messages are routed to the configured agent, responses sent back.
"""

import asyncio
import logging
from datetime import datetime

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

from config import settings

logger = logging.getLogger(__name__)

_app: Application | None = None
_agent_runner = None
_db_factory = None
_ws_manager = None


def set_context(agent_runner, db_factory, ws_manager):
    global _agent_runner, _db_factory, _ws_manager
    _agent_runner = agent_runner
    _db_factory = db_factory
    _ws_manager = ws_manager


async def _start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hello! I'm an AI agent. Send me a message and I'll help you out."
    )


async def _handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _agent_runner:
        await update.message.reply_text("No agent configured for Telegram.")
        return

    user_text = update.message.text
    chat_id = str(update.message.chat_id)
    user_id = str(update.message.from_user.id)

    logger.info(f"Telegram message from {user_id}: {user_text}")

    # Persist inbound message
    if _db_factory:
        from models.message import Message as MessageModel
        async with _db_factory() as db:
            msg = MessageModel(
                agent_id=_agent_runner.config.id,
                channel="telegram",
                channel_user_id=user_id,
                channel_chat_id=chat_id,
                direction="inbound",
                content=user_text,
            )
            db.add(msg)
            await db.commit()

    # Broadcast to WebSocket monitors
    if _ws_manager:
        await _ws_manager.broadcast({
            "type": "channel_message",
            "channel": "telegram",
            "direction": "inbound",
            "content": user_text,
            "chat_id": chat_id,
        })

    # Run agent
    from uuid import uuid4
    execution_id = str(uuid4())
    try:
        result = await _agent_runner.run(user_text, execution_id, thread_id=chat_id)
        response_text = result["output"]
    except Exception as e:
        logger.exception("Agent error on Telegram message")
        response_text = f"Sorry, I encountered an error: {str(e)}"

    # Send response
    await update.message.reply_text(response_text)

    # Persist outbound
    if _db_factory:
        from models.message import Message as MessageModel
        async with _db_factory() as db:
            msg = MessageModel(
                agent_id=_agent_runner.config.id,
                channel="telegram",
                channel_user_id=user_id,
                channel_chat_id=chat_id,
                direction="outbound",
                content=response_text,
            )
            db.add(msg)
            await db.commit()

    if _ws_manager:
        await _ws_manager.broadcast({
            "type": "channel_message",
            "channel": "telegram",
            "direction": "outbound",
            "content": response_text,
            "chat_id": chat_id,
        })


async def start_telegram_bot(token: str, agent_runner, db_factory, ws_manager):
    global _app
    set_context(agent_runner, db_factory, ws_manager)

    _app = Application.builder().token(token).build()
    _app.add_handler(CommandHandler("start", _start_command))
    _app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _handle_message))

    await _app.initialize()
    await _app.start()
    await _app.updater.start_polling(drop_pending_updates=True)
    logger.info("✅ Telegram bot started and polling.")


async def stop_telegram_bot():
    global _app
    if _app:
        await _app.updater.stop()
        await _app.stop()
        await _app.shutdown()
        logger.info("Telegram bot stopped.")
