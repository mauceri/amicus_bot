import importlib
import logging

from nio import JoinError
from nio.events.room_events import RoomMessageText
from nio.rooms import MatrixRoom

from amicus_bot.bot_commands import Command
from amicus_bot.chat_functions import send_text_to_room
from amicus_bot.message_responses import Message

from amicus_bot.interfaces import IObservable, IObserver


logger = logging.getLogger(__name__)


class Callbacks(IObservable):
    def __init__(self, client, store, config):
        """
        Args:
            client (nio.AsyncClient): nio client used to interact with matrix

            store (Storage): Bot storage

            config (Config): Bot configuration parameters
        """
        self.client = client
        self.store = store
        self.config = config
        self.command_prefix = config.command_prefix
        self.observers = {}
        logger.info(f"****************** About to load plugins")
        self.load_plugin("plugins.test")
        logger.info(f"****************** Plugins loaded")

    def load_plugin(self,name:str):
        module = importlib.import_module(name)
        plugin = module.Plugin(self)  # Crée une instance de Echo
        plugin.start()
        return plugin
    
    def subscribe(self, observer: IObserver):
        logger.info(f"***************************Subscribe {observer.prefix()}")
        self.observers[observer.prefix()] = observer

    def unsubscribe(self, observer: IObserver):
        del self.observers[observer.prefix()]

    async def notify(self,room:MatrixRoom, message:str):
        logger.info(f"***************************Notification du message {message}")
        await send_text_to_room(self.client,room,message)


    async def message(self, room, event):
        """Callback for when a message event is received

        Args:
            room (nio.rooms.MatrixRoom): The room the event came from

            event (nio.events.room_events.RoomMessageText): The event defining the message

        """


        
        # Extract the message text
        msg = event.body
        # Ignore messages from ourselves
        if event.sender == self.client.user:
            return

        logger.debug(
            f"Bot message received for room {room.display_name} | "
            f"{room.user_name(event.sender)}: {msg}"
        )

        #logique de la prochaine version
        l = msg.split(' ')
        #le préfixe de la commande est le premier mot
        cmd1 = l[0]
        #le nouveau message est le reste
        msg = ' '.join(l[1:])
        
        #si un objet est indexé par le préfixe de la commande on l'utilise
        o = None;
        try:
            o = self.observers[cmd1]
        except:
            logger.info(f"****************************** {cmd1} not found")
            return
        else:
            o.notify(room,event,msg)
        
        

        # # Process as message if in a public room without command prefix
        # has_command_prefix = msg.startswith(self.command_prefix)
        # if not has_command_prefix and not room.is_group:
        #     # General message listener
        #     message = Message(self.client, self.store, self.config, msg, room, event)
        #     await message.process()
        #     return

        # # Otherwise if this is in a 1-1 with the bot or features a command prefix,
        # # treat it as a command
        # if has_command_prefix:
        #     # Remove the command prefix
        #     msg = msg[len(self.command_prefix) :]

        # command = Command(self.client, self.store, self.config, msg, room, event)
        # await command.process()

    async def invite(self, room, event):
        """Callback for when an invite is received. Join the room specified in the invite"""
        logger.debug(f"Got invite to {room.room_id} from {event.sender}.")

        # Attempt to join 3 times before giving up
        for attempt in range(3):
            result = await self.client.join(room.room_id)
            if type(result) == JoinError:
                logger.error(
                    f"Error joining room {room.room_id} (attempt %d): %s",
                    attempt,
                    result.message,
                )
            else:
                break
        else:
            logger.error("Unable to join room: %s", room.room_id)

        # Successfully joined room
        logger.info(f"Joined {room.room_id}")
