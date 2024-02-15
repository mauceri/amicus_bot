import importlib
import logging
import os
import shutil
import sys
import git
import subprocess
import sys

from nio import JoinError
from nio.events.room_events import RoomMessageText, RoomMessageMedia, RoomEncryptedFile
from nio.rooms import MatrixRoom
import yaml

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from Crypto.Util import Counter
import base64


from amicus_bot.chat_functions import send_text_to_room
from amicus_bot.chat_functions import send_file_to_room

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
        self.path_yaml_plugin = "/data/plugins.yaml"
        self.update_plugins()

    def update_plugins(self):
         with open(self.path_yaml_plugin, 'r') as fichier:
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
            logger.debug(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!Load plugin {err}")
            raise
        
    def unload_plugin(self, plugin_name):
        if plugin_name in self.plugins:

            self.plugins[plugin_name].stop()  # Méthode pour nettoyer le plugin
            del sys.modules[self.plugins[plugin_name].__module__]
            del self.plugins[plugin_name]

    def reload_plugin(self, plugin_name, plugin_path):
        self.load_plugin(plugin_name, plugin_path)

     
    def subscribe(self, observer: IObserver):
        logger.info(f"***************************Subscribe {observer.prefix()}")
        self.observers[observer.prefix()] = observer

    def unsubscribe(self, observer: IObserver):
        del self.observers[observer.prefix()]

    async def notify(self,room:MatrixRoom, event:RoomMessageText, message:str,filepath: str=None, filename:str=None):
        logger.info(f"***************************Notification du message {message} {filepath} {filename}")
        if filename != None:
            await send_file_to_room(self.client,room.room_id,filepath,filename)
        else:
            await send_text_to_room(self.client,room.room_id,message)

    async def message(self, room:MatrixRoom, event:RoomMessageText):
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
        

    def padding_for_b64decode(self,s):
        # Calcule le nombre de caractères de remplissage manquants
        padding = 4 - len(s) % 4
        if padding:
            s += '=' * padding
        return s

    async def message_media(self, room:MatrixRoom,  event:RoomEncryptedFile):
        logger.info(f"****************************** dans message_media {event.body }")
        if isinstance(event, RoomEncryptedFile):
            file_url = event.url
            file_name = event.body  # Nom du fichier tel qu'envoyé dans le message

            devent = None

            logger.info(f"****************************** Avant téléchargement {file_url} {file_name}")
            # Télécharger le fichier
            file_response = await self.client.download(file_url)
            logger.info(f"****************************** Après téléchargement file_response = {file_response}")

            encrypted_content = file_response.body
            # Informations de chiffrement extraites de l'événement
            logger.info(f"£££££££££££££££££££££££££££££££££££££££ key = {event.key}")
            cipher = None
            key_bytes = None
            iv_bytes = None

            try:
                k = event.key["k"]
                iv = event.iv
                padded_key = self.padding_for_b64decode(k)
                key_bytes = base64.urlsafe_b64decode(padded_key)
            except Exception as e:
                logger.warning(f"!!!!!!!!!!!!!!!!!!!!!! Error urlsafe_b64decode(k) {e}")
                raise
            try :
                padded_iv = self.padding_for_b64decode(iv)
                iv_bytes = base64.urlsafe_b64decode(padded_iv)
            except Exception as e:
                logger.warning(f"!!!!!!!!!!!!!!!!!!!!!! Error urlsafe_b64decode(iv) {e}")
                raise
            try :
                # Pour AES.MODE_CTR, PyCryptodome nécessite un objet Counter.
                # La fonction Counter prend comme argument initial_value qui doit être un entier.
                # Vous devez convertir iv_bytes en un entier pour l'utiliser comme valeur initiale du compteur.
                iv_int = int.from_bytes(iv_bytes, byteorder='big')

                # Créer un objet Counter
                ctr = Counter.new(128, initial_value=iv_int)

                cipher = AES.new(key_bytes, AES.MODE_CTR, counter=ctr)
            except Exception as e:
                logger.warning(f"!!!!!!!!!!!!!!!!!!!!!! Error AES.new {e}")
                raise

            decrypted_content = cipher.decrypt(encrypted_content)
            logger.info(f"£££££££££££££££££££££££££££££££££££££££ Contenu décrypté : {decrypted_content}")
            # Sauvegarder le fichier localement
            with open("/data/"+file_name, "wb") as f:
                f.write(decrypted_content)
            self.update_plugins()

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
