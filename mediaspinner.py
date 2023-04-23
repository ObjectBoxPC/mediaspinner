#!/usr/bin/env python3

import base64
import json
import pathlib
import random
import secrets
import subprocess
import sys
import time
import urllib.parse
import urllib.request

SELECT_MAX_ATTEMPTS = 10
HISTORY_SIZE = 10
VLC_HTTP_PORT = 9090

class FileRecord:
    def __init__(self, collection, path):
        self.collection = collection
        self.path = path

class FileSelector:
    def __init__(self, collections, config):
        self._history = []
        self._collections = collections
        self._config = config

    def select_file(self):
        for _ in range(SELECT_MAX_ATTEMPTS):
            file = self._get_random_file()

            same_file_backoff = self._config.get("same_file_backoff", None) or 0
            if same_file_backoff > 0:
                same_file_backoff_hist = self._history[:same_file_backoff]
                if any(file.path == h.path for h in same_file_backoff_hist):
                    continue

            collection_backoff = self._config["collections"].get(file.collection, {}).get("backoff", None) or 0
            if collection_backoff > 0:
                collection_backoff_hist = self._history[:collection_backoff]
                if any(file.collection == h.collection for h in collection_backoff_hist):
                    continue
            break

        self._history.insert(0, file)
        if len(self._history) > HISTORY_SIZE:
            del self._history[HISTORY_SIZE:]
        return file.path

    def _get_random_file(self):
        collection_items = list(self._config["collections"].items())
        collection = random.choices(
            [c[0] for c in collection_items],
            weights=[c[1].get("weight", None) or 1 for c in collection_items]
        )[0]
        path = random.choice(self._collections[collection])
        return FileRecord(collection, path)

class Player:
    def __init__(self):
        self._http_password = secrets.token_urlsafe(16)
        self._process = subprocess.Popen([
            "vlc",
            "--extraintf",
            "http",
            "--http-host",
            "localhost",
            "--http-port",
            str(VLC_HTTP_PORT),
            "--http-password",
            self._http_password,
        ])
        time.sleep(1) # Wait for HTTP server to start

    def play_file(self, file):
        self.send_player_command("pl_empty")
        self.send_player_command("in_enqueue", input=file)
        self.send_player_command("pl_play")

        time.sleep(0.5)
        while True:
            status = self.get_player_status()
            if status["state"] == "stopped":
                break
            time.sleep(0.5)

    def get_player_status(self):
        return self._send_player_status_request({})

    def send_player_command(self, command, **args):
        return self._send_player_status_request(dict(args, command=command))

    def _send_player_status_request(self, query_args):
        query = urllib.parse.urlencode(query_args, quote_via=urllib.parse.quote)
        url = "http://localhost:{}/requests/status.json?{}".format(VLC_HTTP_PORT, query)
        authorization_key = base64.b64encode(":{}".format(self._http_password).encode()).decode()
        authorization_val = "Basic {}".format(authorization_key)
        request = urllib.request.Request(url, headers={ "Authorization": authorization_val })
        with urllib.request.urlopen(request) as response:
            return json.load(response)

    def terminate(self):
        self._process.terminate()

def load_collections(collections_dir):
    collection_path = pathlib.Path(collections_dir)
    return { cp.name: [str(p) for p in cp.iterdir()] \
        for cp in collection_path.iterdir() if cp.is_dir() }

def load_config(config_path):
    with open(config_path) as config_file:
        return json.load(config_file)

if len(sys.argv) < 2:
    print("Usage: {} [config file]".format(sys.argv[0]))
    sys.exit(1)

collections_dir = "."
collections = load_collections(collections_dir)
config = load_config(sys.argv[1])
file_selector = FileSelector(collections, config)
player = Player()

try:
    while True:
        player.play_file(file_selector.select_file())
finally:
    player.terminate()