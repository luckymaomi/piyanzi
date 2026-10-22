# 项目: piyanzi
# 定位: 皮燕子 Skill 静态站（浏览 / 搜索 / 合集单文件下载）
# 页面: 原生 HTML + CSS + JavaScript
# 渲染: marked + DOMPurify
# 合集: 多篇 Markdown 合并为一个 .md
# 版本控制: Git + GitHub Pages

from __future__ import annotations

import argparse
import http.server
import os
import socketserver
import subprocess
import sys
import webbrowser
from functools import partial
from pathlib import Path


PORT = 4570


class LocalThreadingTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def open_browser(url: str) -> None:
    print("[piyanzi] Opening local site...")
    if os.name == "nt":
        try:
            subprocess.Popen(["cmd", "/c", "start", "", "msedge", "--inprivate", url])
            return
        except OSError:
            pass
    webbrowser.open(url)


def create_server(directory: Path, port: int) -> LocalThreadingTCPServer:
    handler = partial(http.server.SimpleHTTPRequestHandler, directory=str(directory))
    return LocalThreadingTCPServer(("127.0.0.1", port), handler)


def serve(directory: Path, port: int, should_open: bool) -> None:
    server = create_server(directory, port)
    with server:
        url = f"http://localhost:{port}/index.html"
        print(f"[piyanzi] Serving {directory} at {url}")
        if should_open:
            open_browser(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n[piyanzi] Server stopped.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve piyanzi locally.")
    parser.add_argument("--port", type=int, default=PORT, help="Local HTTP port.")
    parser.add_argument("--no-open", action="store_true", help="Do not open browser.")
    parser.add_argument("--check", action="store_true", help="Validate paths and exit.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = Path(__file__).resolve().parent
    index_file = project_root / "index.html"

    if args.check:
        if not index_file.exists():
            print("[piyanzi] index.html not found.", file=sys.stderr)
            return 1
        print("[piyanzi] start.index.py check passed.")
        return 0

    if not index_file.exists():
        print("[piyanzi] index.html not found.", file=sys.stderr)
        return 1

    try:
        serve(project_root, args.port, should_open=not args.no_open)
        return 0
    except OSError as error:
        print(f"[piyanzi] Failed to start server: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
