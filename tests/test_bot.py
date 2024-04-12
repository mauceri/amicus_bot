
import datetime
from venv import logger
from nio import JoinError, AsyncClient
from nio.events.room_events import RoomMessageText, RoomMessageMedia, RoomEncryptedFile
from nio.rooms import MatrixRoom
from nio import (
    AsyncClient,
    AsyncClientConfig,
    InviteMemberEvent,
    LocalProtocolError,
    LoginError,
    RoomMessageText,
    RoomMessageMedia,
    RoomMessage,
    MatrixRoom,
    RoomEncryptedFile,
    Event,
)
from amicus_bot.callbacks import Callbacks
from amicus_bot.config import Config
from amicus_bot.storage import Storage

import asyncio
import sys
import datetime
from venv import logger
from nio import JoinError, AsyncClient, RoomMessageText


class TestBot(Callbacks):
    async def notify(self, room: MatrixRoom, event: RoomMessageText, message: str, filepath: str = None, filename: str = None):
        print(f"{message}")
        logger.info(f"{message}")

async def main():
    config_path = "/data/data_test/config.yaml"
    logger.info(f"************************{config_path}")
    
    config = Config(config_path)
    store = Storage(config.database)
    client_config = AsyncClientConfig(
        max_limit_exceeded=0,
        max_timeouts=0,
        store_sync_tokens=True,
        encryption_enabled=True,
    )

    client = AsyncClient(
        config.homeserver_url,
        config.user_id,
        device_id=config.device_id,
        store_path=config.store_path,
        config=client_config,
    )
    logger.info(f"****************** Client {client.user} created")

    tb = TestBot(client, store, config)

    file = open("/data/data_test/messages.txt", "r")
    Lines = file.readlines()

    for line in Lines:
        logger.info(f"{line}")
        date = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")
        l = line.split(' ')
        user = l[0]
        room = l[1]
        msg = ' '.join(l[2:])  # Correction pour joindre correctement le message
        mr = MatrixRoom(room_id=room, own_user_id="Koko")
        e = RoomMessageText(body=msg, formatted_body=None, source={"event_id": "turlututu", "sender": user, "origin_server_ts": datetime.datetime.now()}, format=None)

        await tb.message(mr, e)  # Assurez-vous que tb.notify est bien la méthode asynchrone à appeler

if __name__ == "__main__":
    asyncio.run(main())
