import logging

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


async def send_file(client, room_id, file_path, file_name):
    # Ouvrir le fichier et lire son contenu
    with open(file_path, "rb") as f:
        file_content = f.read()

    # Téléverser le fichier sur le serveur Matrix
    response = await client.upload(file_content, content_type="application/octet-stream", filename=file_name)
    if isinstance(response, UploadResponse):
        # Préparer le contenu du message de type fichier
        content = {
            "body": file_name,  # Nom du fichier affiché dans le salon
            "info": {
                "size": len(file_content),
                # Ajoutez d'autres informations si nécessaire, comme "mimetype"
            },
            "msgtype": "m.file",
            "url": response.content_uri,  # URI du fichier téléversé
        }

        # Envoyer le message avec l'attachement dans le salon
        await client.room_send(
            room_id=room_id,
            message_type="m.room.message",
            content=content
        )
