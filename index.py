# 项目: piyanzi
# 定位: 皮燕子 Skill 静态站（浏览 / 搜索 / 合集单文件下载）
# 页面: 原生 HTML + CSS + JavaScript
# 渲染: marked + DOMPurify
# 合集: 多篇 Markdown 合并为一个 .md
# 版本控制: Git + GitHub Pages

from __future__ import annotations

import argparse
import http.server
import json
import os
import re
import socketserver
import subprocess
import sys
import webbrowser
from functools import partial
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


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


class PageResources(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.paths: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for key, value in attrs:
            if value and (key == "src" or (tag == "link" and key == "href")):
                self.paths.append(value)


def check_project(root: Path) -> None:
    """只检查静态接线，不启动服务，不处理业务文件。"""
    def require_file(path: str, base: Path = root) -> Path:
        target = (base / unquote(path)).resolve()
        if not target.is_relative_to(root) or not target.is_file():
            raise ValueError(f"Missing or invalid local file: {path}")
        return target

    manifest = json.loads(require_file("manifest.json").read_text(encoding="utf-8"))
    entries = manifest.get("files")
    if not isinstance(entries, list) or not entries:
        raise ValueError("Manifest files must be a nonempty list.")
    ids: set[str] = set()
    paths: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("Invalid manifest entry.")
        for field in ("id", "title", "path", "group"):
            if not isinstance(entry.get(field), str) or not entry[field].strip():
                raise ValueError(f"Missing manifest field: {field}")
        if entry["id"] in ids or entry["path"] in paths:
            raise ValueError(f"Duplicate entry: {entry['id']}")
        ids.add(entry["id"])
        paths.add(entry["path"])
        require_file(entry["path"])
        resources = entry.get("resources", [])
        if not isinstance(resources, list) or any(not isinstance(p, str) or not p.strip() for p in resources):
            raise ValueError(f"Invalid resources: {entry['id']}")
        for resource in resources:
            require_file(resource)
    if not {"AGENTS", "fenshen"}.issubset(ids):
        raise ValueError("Missing AGENTS or fenshen entry.")
    remote = urlsplit(manifest.get("remoteSkillBase", ""))
    if remote.scheme not in ("http", "https") or not remote.netloc:
        raise ValueError("Invalid remoteSkillBase.")
    unregistered = {p.relative_to(root).as_posix() for p in (root / "core").glob("*.md")} - paths
    if unregistered:
        raise ValueError(f"Unregistered skills: {sorted(unregistered)}")

    history = manifest.get("history", [])
    if history is not None:
        if not isinstance(history, list):
            raise ValueError("Manifest history must be a list when present.")
        for item in history:
            if not isinstance(item, dict) or not isinstance(item.get("path"), str) or not item["path"].strip():
                raise ValueError("Invalid history entry.")
            require_file(item["path"])

    page = PageResources()
    page.feed(require_file("index.html").read_text(encoding="utf-8"))
    for path in page.paths:
        url = urlsplit(path)
        if not url.scheme and not url.netloc:
            require_file(url.path)
    for module in (root / "assets/js").glob("*"):
        if module.suffix not in (".js", ".mjs"):
            continue
        source = module.read_text(encoding="utf-8")
        for path in re.findall(r'''\bimport\s+(?:[^;]*?\bfrom\s*)?["'](\.[^"']+)["']''', source):
            require_file(path, module.parent)


def main() -> int:
    args = parse_args()
    project_root = Path(__file__).resolve().parent
    index_file = project_root / "index.html"

    if args.check:
        try:
            check_project(project_root)
        except (OSError, ValueError, KeyError, TypeError) as error:
            print(f"[piyanzi] {error}", file=sys.stderr)
            return 1
        print("[piyanzi] Manifest, skills, resources and page/module references verified.")
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
