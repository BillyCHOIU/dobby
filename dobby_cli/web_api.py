"""
Dobby HUD standalone backend.

Serves the static HUD frontend from ./web and adds the minimal
device/voice API the dashboard calls.  Run with:

    python -m dobby_cli.web_api   # or: python web/serve.py

Default: http://127.0.0.1:9119
"""
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = PROJECT_ROOT / "web"

app = FastAPI(title="Dobby HUD API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory device store (replace with real smart-home backend later) ──
_DEVICES: List[Dict[str, Any]] = [
    {"id": "light-1", "name": "客厅主灯", "room": "客厅", "type": "light", "icon": "💡", "on": False, "state": "关"},
    {"id": "ac-1",    "name": "客厅空调", "room": "客厅", "type": "ac",    "icon": "❄️", "on": False, "state": "关"},
    {"id": "curtain-1","name":"客厅窗帘","room": "客厅", "type": "curtain","icon":"🪟", "on": False, "state": "关"},
    {"id": "cam-1",   "name": "门口摄像头","room": "门口", "type": "camera", "icon":"📷", "on": True,  "state": "在线"},
    {"id": "speaker-1","name":"卧室音箱","room": "卧室", "type": "speaker","icon":"🔊", "on": False, "state": "关"},
    {"id": "health-1","name": "健康手表","room": "个人", "type": "health", "icon":"⌚", "on": True,  "state": "监测中"},
]

_VOICE_PROVIDERS: List[Dict[str, Any]] = []


# ── Models ──
class DeviceStateBody(BaseModel):
    type: Optional[str] = None
    state: Optional[str] = None
    on: Optional[bool] = None


class VoiceProviderBody(BaseModel):
    name: str = ""
    endpoint: str = ""
    key: str = ""
    model: str = ""
    voice: str = ""
    format: str = "mp3"
    note: str = ""


class VoiceTestBody(BaseModel):
    endpoint: str = ""
    key: str = ""


class VoiceCommandBody(BaseModel):
    command: str = ""


# ── Device API ──
@app.get("/api/devices")
async def get_devices() -> List[Dict[str, Any]]:
    return _DEVICES


@app.post("/api/devices/{device_id}/state")
async def set_device_state(device_id: str, body: DeviceStateBody):
    dev = next((d for d in _DEVICES if d["id"] == device_id), None)
    if dev is None:
        raise HTTPException(status_code=404, detail="Device not found")
    if body.on is not None:
        dev["on"] = body.on
        dev["state"] = "on" if body.on else "off"
    if body.state is not None:
        dev["state"] = body.state
        dev["on"] = body.state.lower() not in ("off", "关闭", "关", "unknown")
    return {"ok": True, "device": dev}


# ── Voice API ──
@app.post("/api/voice/providers")
async def save_voice_provider(body: VoiceProviderBody):
    provider = body.model_dump()
    _VOICE_PROVIDERS[:] = [p for p in _VOICE_PROVIDERS if p["name"] != provider["name"]]
    _VOICE_PROVIDERS.append(provider)
    return {"ok": True, "provider": provider}


@app.post("/api/voice/test")
async def test_voice_provider(body: VoiceTestBody):
    # TODO: real TTS probe against body.endpoint + body.key
    return {"ok": True, "message": "provider config looks valid (dry-run)"}


@app.post("/api/voice/command")
async def send_voice_command(body: VoiceCommandBody):
    # TODO: dispatch to smart-home command router
    return {"ok": True, "command": body.command, "status": "queued"}


# ── Static frontend (fallback for SPA routes) ──
STATIC_ALLOW = {".html", ".js", ".css", ".json", ".ico", ".png", ".svg", ".jpg", ".jpeg", ".gif", ".webp", ".woff2", ".woff", ".ttf", ".otf"}


@app.get("/{full_path:path}")
async def serve_frontend(request: Any, full_path: str):
    target = (WEB_DIR / full_path).resolve()
    if not target.is_relative_to(WEB_DIR.resolve()):
        raise HTTPException(status_code=403, detail="Path traversal blocked")

    if target.is_dir():
        target = target / "index.html"

    if not target.exists() or not target.is_file():
        # SPA fallback
        fallback = WEB_DIR / "index.html"
        if fallback.exists():
            return FileResponse(fallback)
        raise HTTPException(status_code=404, detail="Not found")

    suffix = target.suffix.lower()
    if suffix not in STATIC_ALLOW:
        raise HTTPException(status_code=404, detail="File type not allowed")

    return FileResponse(target)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=9119, log_level="warning")
