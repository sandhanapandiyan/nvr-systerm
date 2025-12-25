"""
WebSocket consumers for live video streaming
"""

from channels.generic.websocket import AsyncWebsocketConsumer
import json
import logging

logger = logging.getLogger(__name__)


class StreamConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for streaming camera frames
    Much faster than Flask-SocketIO
    """
    
    async def connect(self):
        """Handle WebSocket connection"""
        self.camera_id = self.scope['url_route']['kwargs']['camera_id']
        self.room_group_name = f'camera_{self.camera_id}'
        
        # Join camera group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        logger.info(f"Client connected to camera {self.camera_id}")
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        # Leave camera group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        logger.info(f"Client disconnected from camera {self.camera_id}")
    
    async def receive(self, text_data):
        """Handle messages from WebSocket"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'request_frame':
                # Request a frame from the camera
                await self.send_frame()
        except Exception as e:
            logger.error(f"Error in receive: {e}")
    
    async def send_frame(self):
        """Send frame to client (implement camera manager integration)"""
        # TODO: Integrate with camera manager to get actual frames
        # This will be implemented in the camera manager service
        pass
    
    async def camera_frame(self, event):
        """
        Receive frame from camera group and send to WebSocket
        Called when a frame is broadcast to the group
        """
        await self.send(text_data=json.dumps({
            'type': 'frame',
            'data': event['frame_data']
        }))
