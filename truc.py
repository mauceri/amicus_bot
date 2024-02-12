import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import yaml

class PluginFileChangeHandler(FileSystemEventHandler):
    """Gère les événements pour le fichier de configuration des plugins."""

    def on_modified(self, event):
        """Appelé lorsque le fichier est modifié."""
        if event.src_path == "/Users/mauceric/PRG/amicus-bot/plugins.yaml":
            print("Le fichier plugins.yaml a été modifié.")
            with open("./plugins.yaml", 'r') as fichier:
                contenu = yaml.safe_load(fichier)
                plugins = contenu['plugins']
                for plugin in plugins:
                    if plugin['enabled']:
                        print(f"{plugin['name']} is enabled")
                    else:
                        print(f"{plugin['name']} is disabled")

def start_watchdog():
    path = "/Users/mauceric/PRG/amicus-bot"  # Le dossier contenant le fichier à surveiller
    event_handler = PluginFileChangeHandler()
    observer = Observer()
    observer.schedule(event_handler, path, recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    start_watchdog()