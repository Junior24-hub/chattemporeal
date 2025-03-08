# chat/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import ChatRoom, Message

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'

        # Verificar se o usuário está autenticado
        if self.scope["user"].is_anonymous:
            # Rejeitar conexão se não estiver autenticado
            await self.close()
            return

        # Juntar-se ao grupo da sala
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        # Aceitar a conexão WebSocket
        await self.accept()

        # Enviar mensagens anteriores ao usuário que acabou de se conectar
        messages = await self.get_messages(self.room_name)
        for message in messages:
            await self.send(text_data=json.dumps(message))

        # Notificar outros usuários sobre a nova conexão
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_join',
                'username': self.scope["user"].username
            }
        )

    async def disconnect(self, close_code):
        # Sair do grupo da sala
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

        # Notificar outros usuários sobre a desconexão
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_leave',
                'username': self.scope["user"].username
            }
        )

    # Receber mensagem do WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']

        # Salvar mensagem no banco de dados
        await self.save_message(
            username=self.scope["user"].username,
            room_name=self.room_name,
            message=message
        )

        # Enviar mensagem para o grupo da sala
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'username': self.scope["user"].username,
                'timestamp': await self.get_timestamp()
            }
        )

    # Receber mensagem do grupo
    async def chat_message(self, event):
        # Enviar mensagem para o WebSocket
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'username': event['username'],
            'timestamp': event['timestamp']
        }))

    # Notificação de entrada de usuário
    async def user_join(self, event):
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'message': f"{event['username']} entrou na sala"
        }))

    # Notificação de saída de usuário
    async def user_leave(self, event):
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'message': f"{event['username']} saiu da sala"
        }))

    # Métodos auxiliares para interagir com o banco de dados
    @database_sync_to_async
    def get_messages(self, room_name):
        room = ChatRoom.objects.get(name=room_name)
        messages = Message.objects.filter(room=room).order_by('timestamp')[:50]
        return [
            {
                'message': message.content,
                'username': message.user.username,
                'timestamp': message.timestamp.strftime('%H:%M:%S')
            }
            for message in messages
        ]

    @database_sync_to_async
    def save_message(self, username, room_name, message):
        user = User.objects.get(username=username)
        room = ChatRoom.objects.get(name=room_name)
        Message.objects.create(user=user, room=room, content=message)

    @database_sync_to_async
    def get_timestamp(self):
        from django.utils import timezone
        return timezone.now().strftime('%H:%M:%S')