import http.server
import socketserver

PORT = 8000
Handler = http.server.SimpleHTTPRequestHandler

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"Attacker server listening on port {PORT}")
    print("Waiting for stolen cookies...")
    httpd.serve_forever()