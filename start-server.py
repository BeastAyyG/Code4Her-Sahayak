#!/usr/bin/env python3
"""
Sahayak Safe Maps - Local Development Server

Starts a local HTTP server for testing the app.
Use HTTPS for mobile geolocation tests via GitHub Pages, Vercel, Netlify, or ngrok.
"""

from __future__ import annotations

import http.server
import os
import socket
import socketserver
import sys
import webbrowser
from pathlib import Path


PORT = 8000

if len(sys.argv) > 1:
    try:
        PORT = int(sys.argv[1])
    except ValueError:
        print(f"Invalid port: {sys.argv[1]}. Using default port {PORT}")


SCRIPT_DIR = Path(__file__).parent.absolute()
os.chdir(SCRIPT_DIR)


def get_ip_address() -> str:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except OSError:
        return "127.0.0.1"


class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SCRIPT_DIR), **kwargs)

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()


def print_banner(port: int) -> None:
    ip = get_ip_address()
    print("=" * 60)
    print("SAHAYAK SAFE MAPS - DEV SERVER")
    print("=" * 60)
    print(f"Local:   http://localhost:{port}/safemap.html")
    print(f"Network: http://{ip}:{port}/safemap.html")
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    print("Note: mobile geolocation usually needs HTTPS, not plain LAN HTTP.")


def main() -> int:
    print_banner(PORT)

    try:
        with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
            print(f"Server running at http://localhost:{PORT}/")
            print(f"Open http://localhost:{PORT}/safemap.html to view the map\n")

            try:
                webbrowser.open(f"http://localhost:{PORT}/safemap.html")
                print("Opening browser automatically...")
            except Exception:
                print("Open the URL manually in your browser.")

            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        return 0
    except OSError as error:
        if error.errno in {48, 10048}:
            print(f"\nPort {PORT} is already in use. Try: python start-server.py {PORT + 1}")
        else:
            print(f"\nError: {error}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
