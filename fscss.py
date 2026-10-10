"""FSCSS auto-compiler server.

Scans the codebase for every ``.fscss`` file, compiles it to a sibling
``.css`` file, watches for changes, and serves the compiled CSS over HTTP.

Usage:
    python fscss.py                 # build, then watch and serve
    python fscss.py build           # compile every .fscss once
    python fscss.py watch           # compile, then recompile on change
    python fscss.py serve           # serve compiled CSS over HTTP

Options:
    --port PORT        HTTP port (default 8020)
    --interval SECONDS Watch poll interval (default 0.8)
    --root PATH        Directory to scan (default: this file's folder)
"""

import argparse
import http.server
import os
import socketserver
import sys
import threading
import time
from urllib.parse import unquote, urlparse

from fscss.compiler import compile_fscss

ROOT = os.path.dirname(os.path.abspath(__file__))
EXCLUDE_DIRS = {
    ".git", "__pycache__", "venv", ".venv", "env", ".env",
    "node_modules", ".idea", ".vscode", ".mypy_cache", ".pytest_cache",
}
DEFAULT_PORT = 8020
DEFAULT_INTERVAL = 0.8


def discover(root=ROOT):
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for name in filenames:
            if name.endswith(".fscss"):
                found.append(os.path.join(dirpath, name))
    return sorted(found)


def output_for(source_path):
    return os.path.splitext(source_path)[0] + ".css"


def compile_file(source_path):
    with open(source_path, "r", encoding="utf-8") as fh:
        source = fh.read()
    css = compile_fscss(source)
    out = output_for(source_path)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(css)
    return out, css


def _rel(path, root):
    return os.path.relpath(path, root).replace(os.sep, "/")


def build_all(root=ROOT, verbose=True):
    results = []
    for path in discover(root):
        try:
            out, css = compile_file(path)
            results.append((path, out, len(css), None))
            if verbose:
                print("compiled %s -> %s (%d bytes)" % (_rel(path, root), _rel(out, root), len(css)))
        except Exception as exc:
            results.append((path, None, 0, exc))
            if verbose:
                print("error %s: %s" % (_rel(path, root), exc))
    return results


def watch(root=ROOT, interval=DEFAULT_INTERVAL):
    state = {}
    print("watching for .fscss changes under %s (Ctrl+C to stop)" % root)
    while True:
        for path in discover(root):
            try:
                mtime = os.path.getmtime(path)
            except OSError:
                continue
            if state.get(path) != mtime:
                state[path] = mtime
                try:
                    out, css = compile_file(path)
                    print("compiled %s -> %s (%d bytes)" % (_rel(path, root), _rel(out, root), len(css)))
                except Exception as exc:
                    print("error %s: %s" % (_rel(path, root), exc))
        time.sleep(interval)


def start_watcher(root, interval):
    thread = threading.Thread(target=watch, args=(root, interval), daemon=True)
    thread.start()
    return thread


class FSCSSHandler(http.server.BaseHTTPRequestHandler):
    root = ROOT

    def log_message(self, fmt, *args):
        sys.stdout.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _resolve(self, path):
        path = unquote(urlparse(path).path).lstrip("/")
        if path.endswith(".css"):
            path = path[:-4] + ".fscss"
        candidate = os.path.normpath(os.path.join(self.root, path))
        if os.path.isfile(candidate) and candidate.endswith(".fscss"):
            return candidate
        wanted = os.path.basename(path)
        for source in discover(self.root):
            if os.path.basename(source) == wanted:
                return source
        return None

    def do_GET(self):
        if self.path in ("/", ""):
            self._index()
            return
        source = self._resolve(self.path)
        if not source:
            self._response(404, "text/plain; charset=utf-8", b"not found\n")
            return
        try:
            _, css = compile_file(source)
        except Exception as exc:
            self._response(500, "text/plain; charset=utf-8", ("compile error: %s\n" % exc).encode("utf-8"))
            return
        self._response(200, "text/css; charset=utf-8", css.encode("utf-8"))

    def _index(self):
        lines = ["<h1>FSCSS</h1><ul>"]
        for source in discover(self.root):
            css_url = "/" + _rel(output_for(source), self.root)
            lines.append('<li><code>%s</code> &rarr; <a href="%s">%s</a></li>' % (_rel(source, self.root), css_url, css_url))
        lines.append("</ul>")
        self._response(200, "text/html; charset=utf-8", "\n".join(lines).encode("utf-8"))

    def _response(self, code, content_type, body):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


def serve(root=ROOT, port=DEFAULT_PORT):
    handler = type("Handler", (FSCSSHandler,), {"root": root})
    with ReusableTCPServer(("", port), handler) as httpd:
        print("FSCSS server on http://localhost:%d" % port)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass


def main(argv=None):
    parser = argparse.ArgumentParser(prog="fscss", description="FSCSS auto-compiler server")
    parser.add_argument("command", nargs="?", default="all",
                        choices=["build", "watch", "serve", "all"],
                        help="build = compile once, watch = recompile on change, "
                             "serve = HTTP server, all = build + watch + serve (default)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="HTTP port (default %d)" % DEFAULT_PORT)
    parser.add_argument("--interval", type=float, default=DEFAULT_INTERVAL, help="watch interval in seconds")
    parser.add_argument("--root", default=ROOT, help="directory to scan")
    args = parser.parse_args(argv)

    root = os.path.abspath(args.root)

    if args.command == "build":
        build_all(root)
        return

    if args.command == "watch":
        build_all(root)
        watch(root, args.interval)
        return

    if args.command == "serve":
        start_watcher(root, args.interval)
        serve(root, args.port)
        return

    build_all(root)
    start_watcher(root, args.interval)
    serve(root, args.port)


if __name__ == "__main__":
    main()
