#!/usr/bin/env python3
import asyncio
import importlib
import logging
import os
import sys
from time import sleep

from aiohttp import ClientConnectionError, ServerDisconnectedError
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

logger = logging.getLogger(__name__)

async def main():
    # Read config file

    # A different config file path can be specified as the first command line argument
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    else:
        config_path = "config.yaml"
    config = Config(config_path)
    logger.info(f"****************** Config file read {config}")
    logger.info(f"****************** config.ANY_SCALE_API_KEY={config.ANY_SCALE_API_KEY}")
    os.environ['ANY_SCALE_API_KEY'] = config.ANY_SCALE_API_KEY
    logger.info(f"****************** ANY_SCALE_API_KEY={os.getenv('ANY_SCALE_API_KEY')}")


    # Configure the database
    store = Storage(config.database)

    # Configuration options for the AsyncClient
    client_config = AsyncClientConfig(
        max_limit_exceeded=0,
        max_timeouts=0,
        store_sync_tokens=True,
        encryption_enabled=True,
    )

    # Initialize the matrix client
    client = AsyncClient(
        config.homeserver_url,
        config.user_id,
        device_id=config.device_id,
        store_path=config.store_path,
        config=client_config,
    )
    logger.info(f"****************** Client {client.user} created")
    
 
    # Set up event callbacks
    callbacks = Callbacks(client, store, config)
    client.add_event_callback(callbacks.message, (RoomMessageText,))
    client.add_event_callback(callbacks.invite, (InviteMemberEvent,))
    client.add_event_callback(callbacks.message_media, (RoomEncryptedFile,))
    async def generic_event_handler(*args):
        logger.info(f"@@@@@@@@@@@@@@@@@@@@@@@@@@@@ Dans generic_event_handler {args}")
        if len(args) == 2:  # Événement lié à une salle
            room, event = args
            logger.info(f"@@@@@@@@@@@@@@@@@@@@@@@@@ Événement reçu dans la salle {room.room_id}: {type(event)}")
        elif len(args) == 1:  # Événement non spécifique à une salle
            event, = args
            logger.info(f"@@@@@@@@@@@@@@@@@@@@@@@@@@Événement reçu : {type(event)}")
        else:
            logger.info("@@@@@@@@@@@@@@@@@@@@@@Nombre inattendu d'arguments reçus par le gestionnaire d'événements")

    #client.add_event_callback(generic_event_handler, (Event,))

    logger.info(f"****************** callbacks created")
    # Keep trying to reconnect on failure (with some time in-between)
    while True:
        try:
            # Try to login with the configured username/password
            try:
                logger.info(f"****************** trying to login {config.user_password}")
                login_response = await client.login(
                    password=config.user_password, device_name=config.device_name,
                )
                logger.info(f"****************** after client login {login_response}")
                # Check if login failed
                if type(login_response) == LoginError:
                    logger.error("Failed to login: %s", login_response.message)
                    return False
            except LocalProtocolError as e:
                # There's an edge case here where the user hasn't installed the correct C
                # dependencies. In that case, a LocalProtocolError is raised on login.
                logger.fatal(
                    "Failed to login. Have you installed the correct dependencies? "
                    "https://github.com/poljar/matrix-nio#installation "
                    "Error: %s",
                    e,
                )
                return False

            # Login succeeded!
            logger.info(f"****************** Login success")
            # Sync encryption keys with the server
            # Required for participating in encrypted rooms
            if client.should_upload_keys:
                await client.keys_upload()

            logger.info(f"Logged in as {config.user_id}")
            await client.sync_forever(timeout=30000, full_state=True)

        except (ClientConnectionError, ServerDisconnectedError):
            logger.warning("Unable to connect to homeserver, retrying in 15s...")

            # Sleep so we don't bombard the server with login requests
            sleep(15)
        finally:
     
            # Make sure to close the client connection on disconnect
            await client.close()


#asyncio.get_event_loop().run_until_complete(main())
