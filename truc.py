import json
import string
import sys
from venv import logger
import yaml
import os


def update_plugins(path:string):
    with open(path, 'r') as fichier:
        contenu = yaml.safe_load(fichier)
                
        plugind = json.loads(json.dumps(contenu))

        for plugin in plugind['plugins']:
            print(f"plugin={plugin}")
            name = plugin['name']
            url = plugin['url']
            package = plugin['package']
            folder = "/plugins/"+package
            print(f"+++++++++++++++++++++++++++++++name = {name}, folder = {folder}, url = {url}, package={package}")

            if 'env' in plugin :
                for pair in plugin['env']:
                    os.environ[pair['var']]=pair['val']
                    print(f"****************** {pair['var']}={os.getenv(pair['var'])}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        plugins_path = sys.argv[1]
    else:
        plugins_path = "data/plugins.yaml"
    update_plugins(plugins_path)