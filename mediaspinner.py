#!/usr/bin/env python3

import http
import http.server
import json
import pathlib
import random
import sys

SELECT_MAX_ATTEMPTS = 10
HTTP_SERVER_PORT = 8000
INDEX_PAGE = """<!DOCTYPE html>
<html>
    <head>
        <meta charset="UTF-8"/>
        <title>MediaSpinner</title>
        <style>
        html, body {
            height: 100%;
        }
        #player {
            height: 75%;
        }
        </style>
    </head>
    <body>
        <video controls="controls" id="player"></video>
        <div>
            <button id="skip">Skip</button>
        </div>
        <p>Note: You may need to click to play the first time; afterwards playback should happen automatically.</p>
        <script>
        (function (document, XMLHttpRequest, JSON, encodeURI) {
            var player = document.getElementById('player');
            var skipButton = document.getElementById('skip');
            function getNext() {
                var xhr = new XMLHttpRequest();
                xhr.open('POST', '/playlist/next');
                xhr.addEventListener('load', function () {
                    var responseObj = JSON.parse(xhr.responseText);
                    player.src = encodeURI(responseObj.path);
                    player.play();
                });
                xhr.send();
            }
            player.addEventListener('ended', getNext);
            skipButton.addEventListener('click', getNext);
            getNext();
        })(document, XMLHttpRequest, JSON, encodeURI);
        </script>
    </body>
</html>"""

class MediaRecord:
    def __init__(self, collection, path):
        self.collection = collection
        self.path = path

class MediaSelector:
    def __init__(self, collections, config):
        self._history = []
        self._collections = collections
        self._config = config
        self._history_size = self._get_max_backoff()

    def select_media(self):
        for _ in range(SELECT_MAX_ATTEMPTS):
            media = self._get_random_media()

            same_media_backoff = self._config.get("same_media_backoff", None) or 0
            if same_media_backoff > 0:
                same_media_backoff_hist = self._history[:same_media_backoff]
                if any(media.path == h.path for h in same_media_backoff_hist):
                    continue

            collection_backoff = self._config["collections"].get(media.collection, {}).get("backoff", None) or 0
            if collection_backoff > 0:
                collection_backoff_hist = self._history[:collection_backoff]
                if any(media.collection == h.collection for h in collection_backoff_hist):
                    continue
            break

        self._history.insert(0, media)
        if len(self._history) > self._history_size:
            del self._history[self._history_size:]
        return media.path

    def _get_max_backoff(self):
        same_media_backoff = self._config.get("same_media_backoff", None) or 0
        max_collection_backoff = max(x.get("backoff", None) or 0 for x in self._config["collections"].values())
        return max(0, same_media_backoff, max_collection_backoff)

    def _get_random_media(self):
        collection_items = list(self._config["collections"].items())
        collection = random.choices(
            [c[0] for c in collection_items],
            weights=[c[1].get("weight", None) or 1 for c in collection_items]
        )[0]
        path = random.choice(self._collections[collection])
        return MediaRecord(collection, path)

class RequestHandler(http.server.SimpleHTTPRequestHandler):
    server_version = "MediaSpinner"
    protocol_version = "HTTP/1.1"

    def __init__(self, request, client_address, server):
        super().__init__(request, client_address, server, directory=server.media_base_dir)

    def do_GET(self):
        if self.path == "/":
            self._send_simple_response(http.HTTPStatus.OK, "text/html", INDEX_PAGE)
            return

        super().do_GET()

    def do_POST(self):
        if self.path == "/playlist/next":
            next_media = self.server.media_selector.select_media()
            response_obj = { "path": next_media }
            self._send_simple_response(http.HTTPStatus.OK, "application/json", json.dumps(response_obj))
            return

        self._send_simple_response(http.HTTPStatus.NOT_FOUND, "text/plain", "Not found")

    def _send_simple_response(self, code, content_type, body):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        if type(body) is str:
            body = body.encode("utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

class Server(http.server.ThreadingHTTPServer):
    def __init__(self, media_base_dir, media_selector):
        super().__init__(("localhost", HTTP_SERVER_PORT), RequestHandler)
        self.media_base_dir = media_base_dir
        self.media_selector = media_selector

def load_collections(collections_dir):
    collection_path = pathlib.Path(collections_dir)
    return { cp.name: [str(p.relative_to(collection_path)) for p in cp.iterdir()] \
        for cp in collection_path.iterdir() if cp.is_dir() }

def load_config(config_path):
    with open(config_path) as config_file:
        return json.load(config_file)

if len(sys.argv) < 3:
    print("Usage: {} [config file] [collections folder]".format(sys.argv[0]))
    sys.exit(1)

config_path, collections_dir = sys.argv[1:3]
collections = load_collections(collections_dir)
config = load_config(config_path)
media_selector = MediaSelector(collections, config)
server = Server(collections_dir, media_selector)

try:
    print("Starting server...open http://localhost:{}/".format(HTTP_SERVER_PORT))
    server.serve_forever()
except KeyboardInterrupt:
    print("Exiting")