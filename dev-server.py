#!/usr/bin/env python3
"""Small development utility with independent and combined operations.

Commands:
    python dev-server.py compile
    python dev-server.py serve
    python dev-server.py migrate
    python dev-server.py all
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000


def resolve_directory(directory: str | None = None) -> Path:
    """Return the directory that should be served."""
    if directory:
        return Path(directory).expanduser().resolve()

    for candidate in (ROOT / "public", ROOT / "static", ROOT):
        if candidate.exists():
            return candidate.resolve()

    return (ROOT / "public").resolve()


def compile_fscss_assets(root: str | None = None, watch: bool = False) -> None:
    """Compile FSCSS files using the existing ``fscss.py`` implementation."""
    source_root = Path(root).expanduser().resolve() if root else ROOT
    command = [
        sys.executable,
        str(ROOT / "fscss.py"),
        "watch" if watch else "build",
        "--root",
        str(source_root),
    ]
    subprocess.run(command, cwd=str(ROOT), check=True)


def run_all(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    directory: str | None = None,
    root: str | None = None,
) -> None:
    """Run migration, FSCSS compilation/watch, and the static server together."""
    import threading

    migrate_database()
    source_root = Path(root).expanduser().resolve() if root else ROOT

    # Compile once before the server starts so CSS is ready immediately.
    compile_fscss_assets(str(source_root))

    def watch_fscss_assets() -> None:
        try:
            compile_fscss_assets(str(source_root), watch=True)
        except Exception as exc:
            print(f"FSCSS watcher stopped: {exc}", flush=True)

    watcher = threading.Thread(
        target=watch_fscss_assets,
        name="fscss-watcher",
        daemon=True,
    )
    watcher.start()
    print("FSCSS watcher started.", flush=True)

    run_app_server(host, port)


def run_server(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    directory: str | None = None,
) -> None:
    """Run only the static development server."""
    root = resolve_directory(directory)
    root.mkdir(parents=True, exist_ok=True)

    handler = lambda *args, **kwargs: StaticPreviewHandler(
        *args,
        directory=str(ROOT),
        **kwargs,
    )

    with ThreadingHTTPServer((host, port), handler) as server:
        display_host = "localhost" if host in {"127.0.0.1", "0.0.0.0"} else host
        print(f"Dev server URL: http://{display_host}:{port}", flush=True)
        print(f"Serving static files from: {root}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nStopping dev server...", flush=True)


def run_app_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    """Run Flask with the routes imported from app.py."""
    from app import app as flask_app, register_app_routers

    register_app_routers(flask_app)
    print(f"App dev server URL: http://localhost:{port}", flush=True)
    print("Serving Flask routes from app.py (without starting app.py separately).", flush=True)
    flask_app.run(
        host=host,
        port=port,
        debug=False,
        use_reloader=False,
    )


def migrate_database() -> None:
    """Create missing tables and apply the application's SQLite migrations."""
    from database import init_db

    init_db()
    print("Database initialization and migrations completed.", flush=True)


class StaticPreviewHandler(SimpleHTTPRequestHandler):
    """Serve the landing page and project static assets without Flask."""

    def __init__(self, *args, directory: str, **kwargs):
        super().__init__(*args, directory=directory, **kwargs)

    def do_GET(self) -> None:
        path = unquote(urlsplit(self.path).path)
        if path in {"/", "/index.html"}:
            self._serve_landing_page()
            return
        super().do_GET()

    def _serve_landing_page(self) -> None:
        try:
            from jinja2 import Environment, FileSystemLoader

            environment = Environment(loader=FileSystemLoader(str(ROOT / "Templates")))
            template = environment.get_template("landing.html")
            html = template.render(
                signed_in=False,
                url_for=lambda endpoint, filename: f"/{endpoint}/{filename}",
            ).encode("utf-8")
        except Exception as exc:
            self.send_error(500, f"Unable to render landing page: {exc}")
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html)))
        self.end_headers()
        self.wfile.write(html)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compile FSCSS, run the static server, migrate SQLite, or run all three."
    )
    parser.add_argument(
        "command",
        choices=("compile", "serve", "migrate", "all"),
        help="Operation to run.",
    )
    parser.add_argument("--root", help="FSCSS source root for the compile command.")
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Keep compiling FSCSS files when they change.",
    )
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--directory", help="Directory for the serve command.")
    args = parser.parse_args()

    if args.command == "compile":
        compile_fscss_assets(args.root, args.watch)
    elif args.command == "serve":
        run_server(args.host, args.port, args.directory)
    elif args.command == "migrate":
        migrate_database()
    else:
        run_all(args.host, args.port, args.directory, args.root)


if __name__ == "__main__":
    main()
