"""
WebSocket connection manager for real-time updates
"""

from fastapi import WebSocket
from typing import List, Dict, Any
import logging
import json

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time infrastructure updates"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        logger.info("WebSocket Connection Manager initialized")
    
    async def connect(self, websocket: WebSocket):
        """Accept and register a new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: Dict[Any, Any], websocket: WebSocket):
        """Send message to a specific client"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: Dict[Any, Any]):
        """Broadcast message to all connected clients"""
        disconnected = []
        
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")
                disconnected.append(connection)
        
        # Remove disconnected clients
        for connection in disconnected:
            self.disconnect(connection)
        
        if self.active_connections:
            logger.debug(f"Broadcasted message to {len(self.active_connections)} clients")
    
    async def disconnect_all(self):
        """Disconnect all clients (used during shutdown)"""
        for connection in self.active_connections[:]:  # Copy list to avoid modification during iteration
            try:
                await connection.close()
            except Exception as e:
                logger.error(f"Error closing connection: {e}")
        
        self.active_connections.clear()
        logger.info("All WebSocket connections closed")
    
    def get_connection_count(self) -> int:
        """Get number of active connections"""
        return len(self.active_connections)


# Global WebSocket manager instance
ws_manager = ConnectionManager()
