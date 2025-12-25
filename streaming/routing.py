"""
WebSocket URL routing for streaming
"""

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/stream/(?P<camera_id>\w+)/$', consumers.StreamConsumer.as_asgi()),
]
