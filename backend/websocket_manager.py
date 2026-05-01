from fastapi import WebSocket
from typing import Dict, List
import json
from datetime import datetime
from config import settings

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        print(f"Client {client_id} connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            print(f"Client {client_id} disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: dict, client_id: str):
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            await websocket.send_json(message)
    
    async def broadcast(self, message: dict):
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception as e:
                print(f"Error sending message to {client_id}: {e}")
                self.disconnect(client_id)
    
    async def send_metrics(self, metrics: dict):
        message = {
            "type": "metrics",
            "data": metrics,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.broadcast(message)
    
    async def send_alert(self, alert: dict):
        message = {
            "type": "alert",
            "data": alert,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.broadcast(message)
    
    def get_connected_clients(self) -> List[str]:
        return list(self.active_connections.keys())

manager = ConnectionManager()
