"""
Slack channel integration using Socket Mode.

Requires no public URL — uses SLACK_APP_TOKEN (xapp-...) for the WebSocket
connection and SLACK_BOT_TOKEN (xoxb-...) for sending messages.

Setup:
  1. Create a Slack app at https://api.slack.com/apps
  2. Enable Socket Mode → generate an App-Level Token (xapp-...) → SLACK_APP_TOKEN
  3. Add Bot Token Scopes: chat:write, im:history, im:read, channels:history
  4. Install to workspace → copy Bot User OAuth Token (xoxb-...) → SLACK_BOT_TOKEN
  5. Subscribe to bot events: message.im, message.channels
"""

import asyncio
import logging

logger = logging.getLogger(__name__)

_slack_task: asyncio.Task | None = None
_agent_runner = None
_db_factory = None
_ws_manager = None


async def start_slack_bot(bot_token: str, app_token: str, agent_runner, db_factory, ws_manager):
    global _slack_task, _agent_runner, _db_factory, _ws_manager
    _agent_runner = agent_runner
    _db_factory = db_factory
    _ws_manager = ws_manager

    from slack_bolt.async_app import AsyncApp
    from slack_bolt.adapter.socket_mode.aiohttp import AsyncSocketModeHandler

    app = AsyncApp(token=bot_token)

    @app.event("message")
    async def handle_message(event, say):
        # Ignore messages from bots (including our own replies)
        if event.get("bot_id") or event.get("subtype"):
            return

        user_text = event.get("text", "").strip()
        user_id = event.get("user", "")
        channel_id = event.get("channel", "")

        if not user_text or not _agent_runner:
            return

        logger.info(f"Slack message from {user_id} in {channel_id}: {user_text}")

        # Persist inbound
        if _db_factory:
            from models.message import Message as MessageModel
            async with _db_factory() as db:
                db.add(MessageModel(
                    agent_id=_agent_runner.config.id,
                    channel="slack",
                    channel_user_id=user_id,
                    channel_chat_id=channel_id,
                    direction="inbound",
                    content=user_text,
                ))
                await db.commit()

        # Broadcast to Monitor
        if _ws_manager:
            await _ws_manager.broadcast({
                "type": "channel_message",
                "channel": "slack",
                "direction": "inbound",
                "content": user_text,
                "chat_id": channel_id,
            })

        # Run agent (thread_id = channel_id for per-channel memory)
        from uuid import uuid4
        execution_id = str(uuid4())
        try:
            result = await _agent_runner.run(user_text, execution_id, thread_id=channel_id)
            response_text = result["output"]
        except Exception as e:
            logger.exception("Agent error on Slack message")
            response_text = f"Sorry, I encountered an error: {str(e)}"

        await say(response_text)

        # Persist outbound
        if _db_factory:
            from models.message import Message as MessageModel
            async with _db_factory() as db:
                db.add(MessageModel(
                    agent_id=_agent_runner.config.id,
                    channel="slack",
                    channel_user_id=user_id,
                    channel_chat_id=channel_id,
                    direction="outbound",
                    content=response_text,
                ))
                await db.commit()

        if _ws_manager:
            await _ws_manager.broadcast({
                "type": "channel_message",
                "channel": "slack",
                "direction": "outbound",
                "content": response_text,
                "chat_id": channel_id,
            })

    handler = AsyncSocketModeHandler(app, app_token)

    async def _run():
        await handler.start_async()

    _slack_task = asyncio.ensure_future(_run())
    logger.info("✅ Slack bot started in Socket Mode.")


async def stop_slack_bot():
    global _slack_task
    if _slack_task:
        _slack_task.cancel()
        try:
            await _slack_task
        except asyncio.CancelledError:
            pass
    logger.info("Slack bot stopped.")
