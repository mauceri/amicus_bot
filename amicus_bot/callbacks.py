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
        self.plugins = {}
        logger.info(f"****************** Loading plugins")

        #self.load_plugin("plugins.test")
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
                        self.load_plugin(name,url,folder)
                    else:
                        print(f"++++++++++++++++++++++++++++++{name} is disabled")
                        self.unload_plugin(name)


    def load_plugin(self, plugin_name, plugin_url, plugin_path):
        try:
            print(f"********************************* Load {plugin_name}")
            if plugin_name in self.plugins:
                self.unload_plugin(plugin_name)
            if os.path.isdir(plugin_path):
                shutil.rmtree(plugin_path)
            data_path = "/data/"+plugin_name
            if not os.path.isdir(data_path):
                os.mkdir(data_path)
            git.Repo.clone_from(plugin_url, plugin_path)
            subprocess.run([sys.executable, "-m", "pip", "install", "-e", plugin_path])
            print(f"********************************* Import module {plugin_name}")
            module = importlib.import_module(plugin_name)
            self.plugins[plugin_name] = module.Plugin(self)  # Assumer une classe Plugin standard
            self.plugins[plugin_name].start()
        except Exception as err:
            logger.debug(f"Load plugin {err}")
            raise Exception
        
    def unload_plugin(self, plugin_name):
        if plugin_name in self.plugins:
            self.plugins[plugin_name].deactivate()  # Méthode pour nettoyer le plugin
            del sys.modules[self.plugins[plugin_name].__module__]
            del self.plugins[plugin_name]

    def reload_plugin(self, plugin_name, plugin_path):
        self.load_plugin(plugin_name, plugin_path)

     
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
