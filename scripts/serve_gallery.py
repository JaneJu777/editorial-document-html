#!/usr/bin/env python3
"""Serve _site locally and accept the demo recorder's WebM export."""

import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAX_VIDEO_BYTES = 20 * 1024 * 1024


class GalleryHandler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/save-demo":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_error(400, "Invalid Content-Length")
            return
        if length <= 0 or length > MAX_VIDEO_BYTES:
            self.send_error(413, "Video must be between 1 byte and 20 MB")
            return
        payload = self.rfile.read(length)
        output = ROOT / "gallery" / "assets" / "editorial-document-html-demo.webm"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(payload)
        self.send_response(204)
        self.end_headers()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=4173)
    args = parser.parse_args()
    handler = lambda *items, **kwargs: GalleryHandler(*items, directory=ROOT / "_site", **kwargs)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    print(f"Serving http://127.0.0.1:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
