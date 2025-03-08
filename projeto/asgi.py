# realtime_project/realtime_project/asgi.py
import os
import sys
import django
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

# Adicionar o diretório pai ao path para que o Django possa encontrar os módulos
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

# Definir o módulo de configurações
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'projeto.settings')

# Inicializar o Django
django.setup()

# Importar após o setup do Django
from chat.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})