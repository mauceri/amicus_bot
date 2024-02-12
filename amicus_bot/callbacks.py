import importlib
import logging
import os
import shutil
import sys
import git
import subprocess
import sys

from nio import JoinError
from nio.events.room_events import RoomMessageText
from nio.rooms import MatrixRoom
import yaml

from amicus_bot.chat_functions import send_text_to_room

from amicus_interfaces import IObservable, IObserver


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
        logger.info(f"****************** Loading plugins")

        self.load_plugin("plugins.test")
        with open("/data/plugins.yaml", 'r') as fichier:
                contenu = yaml.safe_load(fichier)
                plugins = contenu['plugins']
                
                for plugin in plugins:
                    name = plugin['name']
                    url = plugin['url']
                    folder = "/plugins/"+name
                    print(f"+++++++++++++++++++++++++++++++name = {name}, folder = {folder}, url = {url}")
                    if plugin['enabled']:
                        print(f"++++++++++++++++++++++++++++++{name} is enabled")
                        if os.path.isdir(folder):
                            shutil.rmtree(folder)
                        git.Repo.clone_from(url, folder)
                        subprocess.run([sys.executable, "-m", "pip", "install", "-e", folder])
        
                        r = self.load_plugin(name)
                        if r != None :
                            logger.info(f"****************** Plugin {name} loaded")
                    else:
                        print(f"++++++++++++++++++++++++++++++{name} is disabled")



        
        # if os.path.isdir("/plugins/perroquet"):
        #     #print(f"*********************Le répertoire plugins/perroquet existe.")
        #     shutil.rmtree("/plugins/perroquet")
        # git.Repo.clone_from("https://github.com/mauceri/perroquet", "/plugins/perroquet")
        # subprocess.run([sys.executable, "-m", "pip", "install", "-e", "/plugins/perroquet"])
        
        # self.load_plugin("perroquet")
        #logger.info(f"****************** Plugins loaded")

    def load_plugin(self,name:str):
        print(f"********************************* Dans load_plugin {name}")
        try:
            module = importlib.import_module(name)
            plugin = module.Plugin(self)  
            plugin.start()
            return plugin
        except Exception:
            raise Exception
        else:
            return None
    
    def subscribe(self, observer: IObserver):
        logger.info(f"***************************Subscribe {observer.prefix()}")
        self.observers[observer.prefix()] = observer

    def unsubscribe(self, observer: IObserver):
        del self.observers[observer.prefix()]

    async def notify(self,room:MatrixRoom, event:RoomMessageText, message:str):
        logger.info(f"***************************Notification du message {message}")
        await send_text_to_room(self.client,room.room_id,message)

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
            f"******************** Bot message received for room {room.display_name} | "
            f"{room.user_name(event.sender)}: {msg}"
        )

        #logique de la prochaine version
        l = msg.split(' ')
        #le préfixe de la commande est le premier mot
        cmd1 = l[0]
        #le nouveau message est le reste
        msg = ' '.join(l[1:])
        
        #si un objet est indexé par le préfixe de la commande on l'utilise
        print(f"****************************commande = {cmd1} et observers = {self.observers}")
        o = None;
        try:
            o = self.observers[cmd1]
        except:
            logger.warning(f"****************************** {cmd1} introuvable essayons perroquet")
            try:
                o = self.observers["!coco"]
            except:
                logger.warning(f"****************************** perroquet n'est pas chargé")
                return
        if o != None:
            await o.notify(room,event,msg)
        else:
            logger.warning(f"****************************** perroquet n'est pas chargé")
        
        

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
