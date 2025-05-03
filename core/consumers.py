from channels.generic.websocket import AsyncWebsocketConsumer
import json
import datetime

class PriceConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        await self.send(text_data=json.dumps({
            "status": "connected",
            "timestamp": str(datetime.datetime.now())
        }))

    async def receive(self, text_data):
        await self.send(text_data=json.dumps({
            "status": "received",
            "echo": json.loads(text_data),
            "received_at": str(datetime.datetime.now())
        }))

