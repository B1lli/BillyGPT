#!/usr/bin/env python3
# coding=utf-8
"""Check that the Flet front end leaves the loading screen."""

import asyncio
import base64
import json
import os
import signal
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import websockets


ROOT = Path(__file__).resolve().parents[1]
SCREENSHOT = ROOT / "verification_frontend.png"


def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def chrome_path():
    candidates = [
        os.getenv("CHROME_BIN"),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
    ]
    return next((path for path in candidates if path and Path(path).exists()), None)


def wait_for_http(port):
    for _ in range(180):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=1):
                return
        except Exception:
            time.sleep(0.5)
    raise RuntimeError("Flet web server did not start")


async def wait_for_page(chrome, app_port, devtools_port, screenshot_path):
    profile = tempfile.mkdtemp(prefix="billygpt-cdp-")
    process = subprocess.Popen(
        [
            chrome,
            "--headless=new",
            "--disable-gpu",
            "--disable-extensions",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--no-first-run",
            "--no-default-browser-check",
            f"--user-data-dir={profile}",
            f"--remote-debugging-port={devtools_port}",
            "--window-size=1400,900",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    try:
        target = None
        for _ in range(50):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{devtools_port}/json", timeout=1) as response:
                    targets = json.loads(response.read().decode())
                target = next(item for item in targets if item.get("type") == "page")
                break
            except Exception:
                time.sleep(0.2)
        if not target:
            raise RuntimeError("Chrome DevTools target was not available")

        next_id = 1
        async with websockets.connect(target["webSocketDebuggerUrl"], max_size=20_000_000) as ws:
            async def send(method, params=None):
                nonlocal next_id
                msg_id = next_id
                next_id += 1
                await ws.send(json.dumps({"id": msg_id, "method": method, "params": params or {}}))
                return msg_id

            async def wait_id(msg_id):
                while True:
                    message = json.loads(await ws.recv())
                    if msg_id == message.get("id"):
                        return message

            for method in ["Runtime.enable", "Page.enable", "Network.enable"]:
                await send(method)
            await wait_id(await send(
                "Emulation.setDeviceMetricsOverride",
                {"width": 1400, "height": 900, "deviceScaleFactor": 1, "mobile": False},
            ))
            await send("Page.navigate", {"url": f"http://127.0.0.1:{app_port}/"})

            state = None
            for _ in range(24):
                await asyncio.sleep(0.5)
                result = await wait_id(await send(
                    "Runtime.evaluate",
                    {
                        "expression": "({loading: !!document.querySelector('#loading'), html: document.body.innerHTML.slice(0, 200)})",
                        "returnByValue": True,
                    },
                ))
                state = result["result"]["result"]["value"]
                if not state["loading"]:
                    break

            if not state or state["loading"]:
                raise RuntimeError("Flet front end stayed on the loading screen")

            await asyncio.sleep(5)
            shot = await wait_id(await send(
                "Page.captureScreenshot",
                {"format": "png", "captureBeyondViewport": False},
            ))
            screenshot_path.write_bytes(base64.b64decode(shot["result"]["data"]))
            if screenshot_path.stat().st_size < 5000:
                raise RuntimeError("Front-end screenshot did not show the rendered interface")
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        shutil.rmtree(profile, ignore_errors=True)


def main():
    chrome = chrome_path()
    if not chrome:
        raise RuntimeError("Chrome or Chromium is required for the front-end startup check")

    app_port = free_port()
    devtools_port = free_port()
    env = os.environ.copy()
    env.setdefault("OPENAI_API_KEY", "test-key")
    env["FLET_FORCE_WEB_SERVER"] = "true"
    env["FLET_SERVER_IP"] = "127.0.0.1"

    server = subprocess.Popen(
        [
            sys.executable,
            "-c",
            (
                "import flet as ft; "
                "from main import ASSETS_DIR, ft_interface; "
                f"ft.app(target=ft_interface, host='127.0.0.1', port={app_port}, "
                "view=ft.AppView.WEB_BROWSER, assets_dir=str(ASSETS_DIR))"
            ),
        ],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        try:
            wait_for_http(app_port)
        except RuntimeError as error:
            if server.poll() is not None:
                stdout, stderr = server.communicate(timeout=3)
                raise RuntimeError(
                    f"{error}\n\nFlet stdout:\n{stdout}\n\nFlet stderr:\n{stderr}"
                )
            raise
        asyncio.run(wait_for_page(chrome, app_port, devtools_port, SCREENSHOT))
    finally:
        os.killpg(server.pid, signal.SIGTERM)
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(server.pid, signal.SIGKILL)
            server.wait(timeout=5)

    print(f"Frontend startup check passed: {SCREENSHOT}")


if __name__ == "__main__":
    main()
