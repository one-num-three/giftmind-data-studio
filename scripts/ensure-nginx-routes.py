#!/usr/bin/env python3
"""Generate an idempotent Nginx site config for a GiftMind deployment.

The default mode is a dry run. Use ``--write`` on the server to write the
config, and add ``--reload`` only after the output has been reviewed.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

DEFAULT_CONFIG_PATH = Path("/etc/nginx/conf.d/giftmind-data-studio.conf")


def _nginx_path(path: Path) -> str:
    """Return a POSIX path suitable for an Nginx config on Linux."""

    return path.resolve().as_posix()


def render_config(
    *,
    project_dir: Path,
    server_name: str,
    backend_url: str,
    listen: int,
) -> str:
    frontend_dist = project_dir / "frontend" / "dist"
    return f"""# Managed by scripts/ensure-nginx-routes.py
server {{
    listen {listen};
    server_name {server_name};

    root {_nginx_path(frontend_dist)};
    index index.html;

    location /api/ {{
        proxy_pass {backend_url}/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }}

    location = /api {{
        proxy_pass {backend_url}/api;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }}

    location / {{
        try_files $uri $uri/ /index.html;
    }}
}}
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=Path.cwd(),
        help="GiftMind repository directory (default: current directory)",
    )
    parser.add_argument(
        "--server-name",
        default="_",
        help="Nginx server_name value (default: _)",
    )
    parser.add_argument(
        "--backend-url",
        default="http://127.0.0.1:8000",
        help="Backend origin without a trailing slash",
    )
    parser.add_argument("--listen", type=int, default=80, help="HTTP listen port")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help=f"Nginx config path (default: {DEFAULT_CONFIG_PATH})",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write the generated config instead of printing it",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Run nginx -t and systemctl reload nginx after --write",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.reload and not args.write:
        print("--reload requires --write", file=sys.stderr)
        return 2
    if args.backend_url.endswith("/"):
        args.backend_url = args.backend_url.rstrip("/")

    config = render_config(
        project_dir=args.project_dir,
        server_name=args.server_name,
        backend_url=args.backend_url,
        listen=args.listen,
    )
    if not args.write:
        print(config, end="")
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(config, encoding="utf-8")
    print(f"wrote {args.output}")
    if args.reload:
        subprocess.run(["nginx", "-t"], check=True)
        subprocess.run(["systemctl", "reload", "nginx"], check=True)
        print("reloaded nginx")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
