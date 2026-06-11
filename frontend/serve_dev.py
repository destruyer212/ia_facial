"""Sirve el frontend con cabeceras no-cache (desarrollo local)."""
from http.server import HTTPServer, SimpleHTTPRequestHandler


class NoCacheHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def log_message(self, fmt, *args):
        print(f"[frontend] {self.address_string()} - {fmt % args}")


def main() -> None:
    port = 5500
    print(f"Sirviendo frontend sin cache en http://127.0.0.1:{port}/")
    print("Ctrl+C para detener")
    HTTPServer(("127.0.0.1", port), NoCacheHandler).serve_forever()


if __name__ == "__main__":
    main()
