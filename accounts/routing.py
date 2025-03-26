from django.urls import re_path
from accounts.consumers import PresenceConsumer  # Import the consumer

websocket_urlpatterns = [
    re_path(r'ws/presence/$', PresenceConsumer.as_asgi()),
]
