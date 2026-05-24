import json
import asyncio
from typing import Dict, List
from fastapi import WebSocket
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, room: str = "global"):
        await websocket.accept()
        async with self._lock:
            if room not in self.active_connections:
                self.active_connections[room] = []
            self.active_connections[room].append(websocket)
        logger.info(f"WebSocket connected to room '{room}'. Total: {len(self.active_connections.get(room, []))}")

    async def disconnect(self, websocket: WebSocket, room: str = "global"):
        async with self._lock:
            if room in self.active_connections:
                try:
                    self.active_connections[room].remove(websocket)
                except ValueError:
                    pass

    async def broadcast(self, message: dict, room: str = "global"):
        data = json.dumps(message, default=str)
        connections = self.active_connections.get(room, []) + self.active_connections.get("global", [])
        dead = []
        for ws in set(connections):
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            for r in list(self.active_connections.keys()):
                try:
                    self.active_connections[r].remove(ws)
                except ValueError:
                    pass

    async def send_log(self, execution_id: str, agent_name: str, log_type: str,
                       content: str, metadata: dict = None):
        await self.broadcast({
            "type": "log",
            "execution_id": execution_id,
            "agent_name": agent_name,
            "log_type": log_type,
            "content": content,
            "metadata": metadata or {},
        })

    async def send_status(self, execution_id: str, status: str, extra: dict = None):
        await self.broadcast({
            "type": "status",
            "execution_id": execution_id,
            "status": status,
            **(extra or {}),
        })


ws_manager = ConnectionManager()
