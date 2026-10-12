"""Local website server; stores only selections produced by valid UI actions."""
import argparse
import json
import os
import secrets
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock

from flow import InvalidAction, Session, write_artifact

ROOT = Path(__file__).resolve().parent


def serve(port, output):
    session = Session(json.loads((ROOT/'catalog.json').read_text()), secrets.token_hex(16))
    write_artifact(output/'result.json', session.artifact())
    lock = Lock()

    class Handler(SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, data, status=200):
            body = json.dumps(data, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == '/state':
                with lock:
                    view = session.view()
                    view['session_id'] = session.session_id
                    view['revision'] = len(session.events)
                    self.reply(view)
                return
            if self.path not in ('/', '/index.html', '/app.js', '/style.css'):
                self.send_error(404)
                return
            super().do_GET()

        def do_POST(self):
            if self.path != '/action':
                self.send_error(404)
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 2048:
                    raise ValueError('Invalid request size')
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict) or set(data) != {'action'}:
                    raise ValueError('An action is required')
                with lock:
                    session.apply(data['action'])
                    write_artifact(output/'result.json', session.artifact())
                    view = session.view()
                    view['session_id'] = session.session_id
                    view['revision'] = len(session.events)
                    self.reply(view)
            except (ValueError, InvalidAction) as exc:
                self.reply({'error': str(exc)}, 400)

    httpd = ThreadingHTTPServer(('127.0.0.1', port), partial(Handler, directory=str(ROOT)))
    print(json.dumps({'port': httpd.server_port}), flush=True)
    httpd.serve_forever()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--output', type=Path,
                        default=Path(os.environ.get('ADHERENCE_OUTPUT_DIR', '/app/output')))
    args = parser.parse_args()
    serve(args.port, args.output)
