#!/usr/local/bin/python3

import json
import os
import requests
import sys

def load_config():
    with(open(os.path.expanduser("~/.pandororc"))) as f:
        j = json.load(f)

        return j["key"], j["token"]

KEY, TOKEN = load_config()
board_id = sys.argv[1]

r = requests.get(f"https://api.trello.com/1/boards/{board_id}/lists?key={KEY}&token={TOKEN}")

r.raise_for_status()

for l in r.json():
    print("%s: %s" % (l["name"], l["id"]))