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
from fastapi.responses import FileResponse, Response
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

# Active voice provider config (last saved)
_VOICE_PROVIDER: Optional[Dict[str, Any]] = None
_VOICE_PROVIDERS_LOG: List[Dict[str, Any]] = []


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
    name: Optional[str] = ""
    endpoint: str = ""
    key: str = ""
    model: Optional[str] = ""
    voice: Optional[str] = ""
    format: Optional[str] = "mp3"


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


# ── Voice API (vendor-agnostic pass-through) ──
def _provider() -> Dict[str, Any]:
    if _VOICE_PROVIDER is None:
        return {}
    return _VOICE_PROVIDER


@app.get("/api/voice/providers")
async def list_voice_providers() -> Dict[str, Any]:
    return {
        "active": _provider(),
        "history": _VOICE_PROVIDERS_LOG[-10:],
    }


@app.post("/api/voice/providers")
async def save_voice_provider(body: VoiceProviderBody):
    global _VOICE_PROVIDER
    provider = body.model_dump()
    _VOICE_PROVIDER = {k: v for k, v in provider.items() if k != "key"}
    _VOICE_PROVIDERS_LOG.append(provider)
    return {"ok": True, "provider": _VOICE_PROVIDER}


@app.post("/api/voice/test")
async def test_voice_provider(body: VoiceTestBody):
    provider = {
        "name": body.name or _provider().get("name", "custom"),
        "endpoint": body.endpoint or _provider().get("endpoint", ""),
        "key": body.key or _provider().get("key", ""),
        "model": body.model or _provider().get("model", ""),
        "voice": body.voice or _provider().get("voice", ""),
        "format": body.format or _provider().get("format", "mp3"),
    }
    if not provider["endpoint"] or not provider["key"]:
        return {"ok": False, "message": "missing endpoint or key", "provider": {k: (v if k != "key" else "***") for k, v in provider.items()}}

    try:
        import httpx
        headers = {"Authorization": f"Bearer {provider['key']}", "Content-Type": "application/json"}
        payload = {"model": provider["model"], "input": "你好，我是 Dobby", "voice": provider["voice"]}
        if provider["format"]:
            payload["response_format"] = provider["format"]

        r = httpx.post(provider["endpoint"], headers=headers, json=payload, timeout=15.0)
        ctype = r.headers.get("content-type", "")
        if r.status_code == 200 and ("audio" in ctype or "octet" in ctype):
            return {"ok": True, "message": f"TTS OK ({r.status_code}, {len(r.content)} bytes, {ctype})", "provider": {k: (v if k != "key" else "***") for k, v in provider.items()}}
        return {"ok": False, "message": f"TTS failed: HTTP {r.status_code} {r.text[:300]}", "provider": {k: (v if k != "key" else "***") for k, v in provider.items()}}
    except Exception as e:
        return {"ok": False, "message": f"request error: {type(e).__name__}: {e}", "provider": {k: (v if k != "key" else "***") for k, v in provider.items()}}


@app.post("/api/voice/command")
async def send_voice_command(body: VoiceCommandBody):
    provider = _provider()
    if not provider:
        return {"ok": False, "command": body.command, "status": "no_provider_configured", "message": "请先在语音配置里填写 API 端点与 Key"}

    try:
        import httpx
        headers = {"Authorization": f"Bearer {provider.get('key','')}", "Content-Type": "application/json"}
        payload = {"model": provider.get("model", ""), "input": body.command, "voice": provider.get("voice", "")}
        fmt = provider.get("format", "mp3")
        if fmt:
            payload["response_format"] = fmt

        r = httpx.post(provider.get("endpoint", ""), headers=headers, json=payload, timeout=20.0)
        ctype = r.headers.get("content-type", "")
        if r.status_code == 200 and ("audio" in ctype or "octet" in ctype):
            # Return audio blob directly so the browser can play it
            return Response(content=r.content, media_type=ctype, headers={"X-Command": body.command, "X-Voice-Provider": provider.get("name", "custom")})
        return {"ok": False, "command": body.command, "status": "tts_failed", "message": f"HTTP {r.status_code}: {r.text[:300]}"}
    except Exception as e:
        return {"ok": False, "command": body.command, "status": "error", "message": f"{type(e).__name__}: {e}"}


# ── Static frontend (fallback for SPA routes) ──
STATIC_ALLOW = {".html", ".js", ".css", ".json", ".ico", ".png", ".svg", ".jpg", ".jpeg", ".gif", ".webp", ".woff2", ".woff", ".ttf", ".otf", ".mp3", ".wav", ".pcm", ".opus"}


@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    target = (WEB_DIR / full_path).resolve()
    if not target.is_relative_to(WEB_DIR.resolve()):
        raise HTTPException(status_code=403, detail="Path traversal blocked")

    if target.is_dir():
        target = target / "index.html"

    if not target.exists() or not target.is_file():
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
