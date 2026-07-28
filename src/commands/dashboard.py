"""The `dashboard` subcommand: run (or install as a daemon) the local usage dashboard."""
from __future__ import annotations

import argparse
from pathlib import Path

from src.config import Config
from src.dashboard import daemon
from src.dashboard.server import make_server

_DEFAULT_PORT = 8420
_FRONTEND_DIST = Path(__file__).resolve().parents[1] / "dashboard" / "static"


class DashboardCommand:
    name = "dashboard"
    help = "run the local usage dashboard"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--port", type=int, default=_DEFAULT_PORT,
                             help=f"port to bind (default: {_DEFAULT_PORT})")
        parser.add_argument("--daemon", action="store_true",
                             help="install a persistent background dashboard service")
        parser.add_argument("--stop", action="store_true",
                             help="remove the persistent dashboard service")

    def run(self, args: argparse.Namespace) -> int:
        if not (1 <= args.port <= 65535):
            print(f"Error: --port must be between 1 and 65535, got {args.port}")
            return 1

        if args.stop:
            try:
                daemon.uninstall()
            except RuntimeError as exc:
                print(f"Error: {exc}")
                return 1
            print("Dashboard daemon stopped.")
            return 0

        if args.daemon:
            try:
                started = daemon.install(args.port)
            except RuntimeError as exc:
                print(f"Error: {exc}")
                return 1
            if started:
                print(f"Dashboard daemon installed — running at "
                      f"http://127.0.0.1:{args.port}.")
            else:
                print(f"Dashboard daemon already running at "
                      f"http://127.0.0.1:{args.port}.")
            return 0

        if not _FRONTEND_DIST.exists():
            print(f"Error: frontend build not found at {_FRONTEND_DIST}. "
                  f"The built dashboard is committed by CI — pull the latest main, "
                  f"or build it yourself: cd frontend && pnpm install && pnpm run build")
            return 1

        cfg = Config.load()
        db_path = Path(args.db) if args.db else cfg.db_path
        server = make_server(db_path, _FRONTEND_DIST, args.port)
        print(f"Dashboard running at http://127.0.0.1:{args.port} (Ctrl-C to stop)")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
        return 0
