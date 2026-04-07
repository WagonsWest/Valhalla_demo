"""Simple dev server: serves static files and proxies /route, /status etc. to Valhalla."""
import http.server
import urllib.request
import json

VALHALLA = "http://localhost:8002"
PORT = 3000

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def do_GET(self):
        if self.path.startswith(("/status", "/locate", "/isochrone")):
            self._proxy("GET")
        else:
            super().do_GET()

    def do_POST(self):
        if self.path.startswith(("/route", "/optimized_route", "/isochrone", "/locate", "/map_matching")):
            self._proxy("POST")
        else:
            self.send_error(404)

    def _proxy(self, method):
        try:
            body = None
            if method == "POST":
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length) if length else None
            req = urllib.request.Request(VALHALLA + self.path, data=body, method=method)
            req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req) as resp:
                data = resp.read()
                self.send_response(resp.status)
                self._cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(data)
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            self._cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(e.read())
        except Exception as e:
            self.send_response(502)
            self._cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, fmt, *args):
        print(f"  {args[0]}")

if __name__ == "__main__":
    print(f"Serving on http://localhost:{PORT}")
    print(f"Proxying API requests to {VALHALLA}")
    http.server.HTTPServer(("", PORT), Handler).serve_forever()
