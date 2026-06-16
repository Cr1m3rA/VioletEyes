import re, urllib.request, urllib.error
import http.server, socketserver, threading, os, sys, time

ROOT = r"C:\Users\Jerome\Documents\VioletEyes\tests\fixtures"
os.chdir(ROOT)

class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a, **kw): pass

PORT = 8765
srv = socketserver.TCPServer(("127.0.0.1", PORT), Q)
threading.Thread(target=srv.serve_forever, daemon=True).start()
time.sleep(0.3)
try:
    r = urllib.request.urlopen(f"http://127.0.0.1:{PORT}/code-audit-report.html", timeout=5)
    print("status:", r.status, "len:", len(r.read()))
finally:
    srv.shutdown()