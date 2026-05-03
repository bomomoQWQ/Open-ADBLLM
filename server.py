"""Open-ADBLLM HTTP API Server.

ADB command API + web console with 3-level permission system.
Reuses phone_agent/adb/ module from Open-AutoGLM.
"""

import asyncio
import base64
import os
import secrets
import subprocess
import time
import uuid
from io import BytesIO
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from PIL import Image

from phone_agent.adb import back, get_current_app, get_screenshot, home, launch_app
from phone_agent.adb.connection import list_devices
from phone_agent.adb.device import double_tap, long_press, swipe, tap
from phone_agent.adb.input import clear_text, type_text


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

_PORT = int(os.getenv("ADBLLM_PORT", "8000"))
_CONSOLE_USER = os.getenv("ADBLLM_CONSOLE_USER", "")
_CONSOLE_PASS = os.getenv("ADBLLM_CONSOLE_PASS", "")

# ---------------------------------------------------------------------------
# Permission state
# ---------------------------------------------------------------------------

_yellow_enabled = False
_red_keys: dict[str, float] = {}  # key → expiry timestamp
_log_queue: asyncio.Queue[str] = asyncio.Queue()

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="Open-ADBLLM", version="0.1.0")


def _log(msg: str) -> None:
    safe = msg.replace("\n", " ")[:200]
    print(safe)
    try:
        _log_queue.put_nowait(safe)
    except asyncio.QueueFull:
        pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _adb_shell(cmd: str, timeout: int = 5) -> str:
    result = subprocess.run(
        ["adb", "shell"] + cmd.split(), capture_output=True, text=True, timeout=timeout
    )
    return (result.stdout + result.stderr).strip()

def _check_adb() -> bool:
    try:
        r = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=3)
        return r.returncode == 0 and "\tdevice" in r.stdout
    except Exception:
        return False

# ---------------------------------------------------------------------------
# Permission decorators
# ---------------------------------------------------------------------------

from functools import wraps

def require_yellow(fn):
    @wraps(fn)
    async def wrapper(*a, **kw):
        if not _yellow_enabled:
            raise HTTPException(403, "Yellow permissions disabled. Enable via web console.")
        return await fn(*a, **kw)
    return wrapper

def require_red(fn):
    @wraps(fn)
    async def wrapper(request: Request, *a, **kw):
        auth = request.headers.get("Authorization", "")
        key = auth.removeprefix("Bearer ").strip()
        now = time.time()
        # Clean expired keys
        for k in list(_red_keys):
            if _red_keys[k] < now:
                del _red_keys[k]
        if key not in _red_keys:
            raise HTTPException(423, "Red permission requires a one-time key. Generate via web console.")
        del _red_keys[key]
        return await fn(request, *a, **kw)
    return wrapper

# ---------------------------------------------------------------------------
# Console auth middleware
# ---------------------------------------------------------------------------

from starlette.middleware.base import BaseHTTPMiddleware
from base64 import b64decode
import secrets as _secrets_mod

if _CONSOLE_USER and _CONSOLE_PASS:
    class _ConsoleAuth(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            if not request.url.path.startswith("/console") and request.url.path != "/":
                return await call_next(request)
            auth = request.headers.get("Authorization", "")
            if not auth.startswith("Basic "):
                return HTMLResponse("Unauthorized", 401, {"WWW-Authenticate": "Basic"})
            try:
                up = b64decode(auth[6:]).decode().split(":", 1)
                if up[0] == _CONSOLE_USER and up[1] == _CONSOLE_PASS:
                    return await call_next(request)
            except Exception:
                pass
            return HTMLResponse("Unauthorized", 401, {"WWW-Authenticate": "Basic"})
    app.add_middleware(_ConsoleAuth)

# ---------------------------------------------------------------------------
# 🟢 Green APIs
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    adb_ok = _check_adb()
    return {"status": "ok" if adb_ok else "degraded", "adb_available": adb_ok}


@app.get("/screenshot")
def screenshot():
    img = Image.open(BytesIO(base64.b64decode(get_screenshot().base64_data)))
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=80)
    _log("Screenshot taken")
    return {"image": base64.b64encode(buf.getvalue()).decode(), "width": img.width, "height": img.height}


@app.get("/screen/info")
def screen_info():
    size = _adb_shell("wm size").replace("Physical size: ", "").strip()
    density = _adb_shell("wm density").replace("Physical density: ", "").strip()
    w, h = size.split("x") if "x" in size else ("0", "0")
    return {"width": int(w), "height": int(h), "dpi": int(density) if density.isdigit() else 0}


@app.post("/tap")
async def api_tap(req: Request):
    data = await req.json()
    x, y = data["x"], data["y"]
    tap(x, y)
    _log(f"Tap ({x},{y})")
    return {"ok": True}


@app.post("/swipe")
async def api_swipe(req: Request):
    data = await req.json()
    s, e = data["start"], data["end"]
    dur = data.get("duration", 300)
    swipe(s[0], s[1], e[0], e[1], duration_ms=dur)
    _log(f"Swipe {s}→{e}")
    return {"ok": True}


@app.post("/long-press")
async def api_long_press(req: Request):
    data = await req.json()
    x, y = data["x"], data["y"]
    dur = data.get("duration", 1000)
    long_press(x, y, duration_ms=dur)
    _log(f"LongPress ({x},{y})")
    return {"ok": True}


@app.post("/type")
async def api_type(req: Request):
    data = await req.json()
    txt = str(data["text"])
    type_text(txt)
    _log(f"Type: {txt[:30]}")
    return {"ok": True}


@app.post("/key")
async def api_key(req: Request):
    data = await req.json()
    key = data["key"]
    codes = {"back": 4, "home": 3, "recent": 187, "power": 26,
             "volume_up": 24, "volume_down": 25, "enter": 66}
    if key not in codes:
        raise HTTPException(400, f"Unknown key: {key}")
    subprocess.run(["adb", "shell", "input", "keyevent", str(codes[key])], timeout=5)
    _log(f"Key: {key}")
    return {"ok": True}


@app.post("/app/launch")
async def api_launch(req: Request):
    data = await req.json()
    pkg = data["package"]
    launch_app(pkg)
    _log(f"Launch: {pkg}")
    return {"ok": True}


@app.get("/app/current")
def app_current():
    return {"package": get_current_app()}


@app.get("/app/list")
def app_list():
    raw = _adb_shell("pm list packages")
    pkgs = [l.replace("package:", "").strip() for l in raw.split("\n") if l.startswith("package:")]
    return {"packages": pkgs}


@app.get("/device/info")
def device_info():
    model = _adb_shell("getprop ro.product.model")
    version = _adb_shell("getprop ro.build.version.release")
    battery = _adb_shell("dumpsys battery | grep level").strip()
    return {"model": model, "android_version": version, "battery": battery}


# ---------------------------------------------------------------------------
# 🟡 Yellow APIs
# ---------------------------------------------------------------------------

@app.post("/device/reboot")
@require_yellow
async def api_reboot(req: Request):
    subprocess.run(["adb", "reboot"], timeout=5)
    _log("REBOOT")
    return {"ok": True}


@app.post("/device/wake")
@require_yellow
async def api_wake(req: Request):
    subprocess.run(["adb", "shell", "input", "keyevent", "224"], timeout=5)
    _log("Wake")
    return {"ok": True}


@app.post("/device/sleep")
@require_yellow
async def api_sleep(req: Request):
    subprocess.run(["adb", "shell", "input", "keyevent", "223"], timeout=5)
    _log("Sleep")
    return {"ok": True}


@app.post("/device/brightness")
@require_yellow
async def api_brightness(req: Request):
    data = await req.json()
    lv = min(255, max(0, int(data["level"])))
    _adb_shell(f"settings put system screen_brightness {lv}")
    _log(f"Brightness: {lv}")
    return {"ok": True}


@app.post("/wifi/toggle")
@require_yellow
async def api_wifi(req: Request):
    state = _adb_shell("settings get global wifi_on")
    new = "disable" if state == "1" else "enable"
    _adb_shell(f"svc wifi {new}")
    _log(f"WiFi {new}d")
    return {"ok": True}


@app.post("/app/install")
@require_yellow
async def api_install(req: Request):
    raise HTTPException(501, "APK install via API not implemented. Use ADB manually or the /shell endpoint.")


@app.post("/app/uninstall")
@require_yellow
async def api_uninstall(req: Request):
    data = await req.json()
    pkg = data["package"]
    subprocess.run(["adb", "uninstall", pkg], timeout=10)
    _log(f"Uninstall: {pkg}")
    return {"ok": True}


@app.post("/app/clear")
@require_yellow
async def api_clear(req: Request):
    data = await req.json()
    pkg = data["package"]
    _adb_shell(f"pm clear {pkg}")
    _log(f"Clear data: {pkg}")
    return {"ok": True}


@app.post("/shell")
@require_yellow
async def api_shell(req: Request):
    data = await req.json()
    cmd = data["command"]
    result = _adb_shell(cmd, timeout=data.get("timeout", 10))
    _log(f"Shell: {cmd[:50]}")
    return {"output": result}


# ---------------------------------------------------------------------------
# 🔴 Red APIs
# ---------------------------------------------------------------------------

@app.post("/device/factory-reset")
@require_red
async def api_factory_reset(req: Request):
    subprocess.run(["adb", "shell", "reboot", "recovery"], timeout=5)
    _log("FACTORY RESET")
    return {"ok": True, "warning": "Device rebooting to recovery"}


@app.post("/oem/unlock")
@require_red
async def api_oem_unlock(req: Request):
    subprocess.run(["adb", "shell", "reboot", "bootloader"], timeout=5)
    _log("OEM UNLOCK → bootloader")
    return {"ok": True, "warning": "Rebooting to bootloader. Run: fastboot oem unlock"}


@app.post("/root/enable")
@require_red
async def api_root_enable(req: Request):
    _log("Root request (not implemented in API)")
    return {"ok": True, "warning": "Root must be enabled manually via recovery"}


# ---------------------------------------------------------------------------
# Admin endpoints (for web console)
# ---------------------------------------------------------------------------

@app.get("/admin/yellow")
def admin_get_yellow():
    return {"yellow_enabled": _yellow_enabled}

@app.post("/admin/yellow")
async def admin_toggle_yellow(req: Request):
    global _yellow_enabled
    _yellow_enabled = not _yellow_enabled
    _log(f"Yellow permissions: {'ON' if _yellow_enabled else 'OFF'}")
    return {"yellow_enabled": _yellow_enabled}

@app.post("/admin/gen-key")
async def admin_gen_key():
    key = uuid.uuid4().hex
    _red_keys[key] = time.time() + 60
    _log(f"Red key generated: {key[:8]}... (expires 60s)")
    return {"key": key, "expires_in": 60}


@app.get("/stream")
async def log_stream():
    async def event_stream():
        while True:
            msg = await _log_queue.get()
            yield f"data: {msg}\n\n"
    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# Web Console (single page)
# ---------------------------------------------------------------------------

_CONSOLE_HTML = """<!DOCTYPE html>
<html lang="zh">
<head><meta charset="UTF-8"><title>Open-ADBLLM Console</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}body{font-family:monospace;display:flex;height:100vh;background:#1a1a2e;color:#e0e0e0}
#log{flex:1;overflow-y:auto;padding:12px;background:#16213e;border-right:1px solid #333}
#panel{width:320px;padding:16px;display:flex;flex-direction:column;gap:12px}
h3{color:#00d4aa}
.btn{padding:10px;border:none;border-radius:4px;cursor:pointer;font-weight:bold}
.btn-green{background:#00d4aa;color:#111}
.btn-yellow{background:#f0a500;color:#111}
.btn-red{background:#e94560;color:#fff}
.btn-off{background:#555;color:#aaa}
.key-box{background:#0f3460;padding:10px;border-radius:4px;word-break:break-all;font-size:13px}
.log-line{padding:2px 0;border-bottom:1px solid #1a1a2e;font-size:13px}
.countdown{color:#e94560}
</style></head>
<body>
<div id="log"><h3>📜 Log</h3></div>
<div id="panel">
<h3>🎛 Open-ADBLLM</h3>
<button class="btn btn-yellow" id="btn-yellow" onclick="toggleYellow()">🟡 Yellow: OFF</button>
<button class="btn btn-red" id="btn-genkey" onclick="genKey()">🔴 Generate Red Key</button>
<div id="key-area"></div>
<div style="margin-top:auto;font-size:11px;color:#666">v0.1.0</div>
</div>
<script>
const es=new EventSource("/stream");
es.onmessage=e=>{let d=document.createElement("div");d.className="log-line";d.textContent=e.data;
let log=document.getElementById("log");log.appendChild(d);log.scrollTop=log.scrollHeight};
async function toggleYellow(){
let r=await fetch("/admin/yellow",{method:"POST"});let d=await r.json();
let btn=document.getElementById("btn-yellow");
btn.textContent=d.yellow_enabled?"🟡 Yellow: ON":"🟡 Yellow: OFF";
btn.className=d.yellow_enabled?"btn btn-yellow":"btn btn-off"}
async function genKey(){
let r=await fetch("/admin/gen-key",{method:"POST"});let d=await r.json();
let area=document.getElementById("key-area");
area.innerHTML=`<div class="key-box">${d.key}<br><span class="countdown">Expires in <span id="timer">60</span>s</span></div>`;
let t=60;let i=setInterval(()=>{t--;document.getElementById("timer").textContent=t;if(t<=0){clearInterval(i);area.innerHTML=""}},1000)}
fetch("/admin/yellow").then(r=>r.json()).then(d=>{
let btn=document.getElementById("btn-yellow");
btn.textContent=d.yellow_enabled?"🟡 Yellow: ON":"🟡 Yellow: OFF";
btn.className=d.yellow_enabled?"btn btn-yellow":"btn btn-off"})
</script></body></html>"""


@app.get("/", response_class=HTMLResponse)
def console():
    return _CONSOLE_HTML
