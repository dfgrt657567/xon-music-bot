import http.server
import socketserver
import os
import sys

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
        sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    except Exception:
        pass

PORT = 8000
WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def log_message(self, format, *args):
        # Clean logging format
        print(f"[HTTP {self.log_date_time_string()}] {args[0]} {args[1]}")

def run_server():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print("=" * 60)
        print(f"[+] AeroMusic Web Dashboard is LIVE at:")
        print(f"👉 Local URL:   http://localhost:{PORT}")
        print(f"👉 Network URL: http://127.0.0.1:{PORT}")
        print(f"📁 Serving:     {WEB_DIR}")
        print("=" * 60)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[*] Web server stopped.")

if __name__ == "__main__":
    run_server()
