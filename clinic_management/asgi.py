import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import re_path
from accounts.consumers import PresenceConsumer  # Import your consumer

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_management.settings')
print("Initializing ASGI application...")
application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter([
            re_path(r"^ws/presence/$", PresenceConsumer.as_asgi()),  # .as_asgi() is necessary
        ])
    ),
})
