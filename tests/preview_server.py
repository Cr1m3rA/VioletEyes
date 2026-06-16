#!/usr/bin/env python3
"""Tiny static-file server for previewing the smoke-test HTML report."""
import http.server, socketserver, sys, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
with socketserver.TCPServer(("127.0.0.1", port), http.server.SimpleHTTPRequestHandler) as httpd:
    print(f"serving {os.getcwd()} at http://127.0.0.1:{port}/")
    httpd.serve_forever()