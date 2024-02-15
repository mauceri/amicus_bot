import logging
import os
import aiofiles

from markdown import markdown
from nio import SendRetryError, UploadResponse

logger = logging.getLogger(__name__)


async def send_text_to_room(
    client, room_id, message, notice=True, markdown_convert=True
):
    """Send text to a matrix room

    Args:
        client (nio.AsyncClient): The client to communicate to matrix with

        room_id (str): The ID of the room to send the message to

        message (str): The message content

        notice (bool): Whether the message should be sent with an "m.notice" message type
            (will not ping users)

        markdown_convert (bool): Whether to convert the message content to markdown.
            Defaults to true.
    """
    # Determine whether to ping room members or not
    msgtype = "m.notice" if notice else "m.text"

    content = {
        "msgtype": msgtype,
        "format": "org.matrix.custom.html",
        "body": message,
    }

    if markdown_convert:
        content["formatted_body"] = markdown(message)

    try:
        await client.room_send(
            room_id, "m.room.message", content, ignore_unverified_devices=True,
        )
    except SendRetryError:
        logger.exception(f"Unable to send message response to {room_id}")


async def send_file_to_room(client, room_id, file_path, file_name):
    # Utiliser aiofiles pour ouvrir le fichier de manière asynchrone
    async with aiofiles.open(file_path, "rb") as f:
        # Téléverser le fichier sur le serveur Matrix
        logger.info(f"***************************Envoi {file_name} sur Matrix")
        response_tuple  = await client.upload(f, content_type="application/octet-stream", filename=file_name)
       
        if response_tuple  and isinstance(response_tuple[0], UploadResponse):
            response = response_tuple[0]
            # Préparer le contenu du message de type fichier
            content = {
                "body": file_name,  # Nom du fichier affiché dans le salon
                "info": {
                    "size": os.path.getsize(file_path),
                    # Ajoutez d'autres informations si nécessaire, comme "mimetype"
                },
                "msgtype": "m.file",
                "url": response.content_uri,  # URI du fichier téléversé
            }

            # Envoyer le message avec l'attachement dans le salon
            logger.info(f"***************************Envoi {file_name}")
            await client.room_send(
                room_id=room_id,
                message_type="m.room.message",
                content=content
            )
        else:
            logger.info(f"***************************Quitte {response}")