import asyncio
import base64
import io
import logging
import threading
import wave
from typing import List, Set

import numpy as np
from aiohttp import web


LOGGER = logging.getLogger("Server2")

HOST = "0.0.0.0"
HTTP_PORT = 8080

# Connected SSE clients each get their own queue
_client_queues: Set[asyncio.Queue] = set()

# Server state
_loop: asyncio.AbstractEventLoop | None = None
_app: web.Application | None = None
_runner: web.AppRunner | None = None
_site: web.TCPSite | None = None

_started = False
_lock = threading.Lock()
_ready = threading.Event()


# ---------------- HTML (minimal) ----------------
_HTML = """<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\" />
  <title>NicoWiredBot TTS (SSE)</title>
  <style>
    body { background:#111; color:#eee; font-family:sans-serif; margin:0; padding:10px; }
    #s { background:#222; display:inline-block; padding:4px 8px; margin:0 0 8px 0; font-size:13px; }
  </style>
  <meta http-equiv=\"Cache-Control\" content=\"no-store\" />
  <meta http-equiv=\"Pragma\" content=\"no-cache\" />
  <meta http-equiv=\"Expires\" content=\"0\" />
  <script>
    let es, ctx, playing=false, q=[];
    const START_OFFSET = 0.10; // schedule a bit ahead for safety

    function ensureCtx(){
      if (!ctx) {
        const AC = window.AudioContext || window.webkitAudioContext;
        try {
          // 48k aligns with OBS; browsers may ignore if unsupported
          ctx = new AC({ sampleRate: 48000, latencyHint: 'interactive' });
        } catch (e) {
          ctx = new AC();
        }
      }
      if (ctx.state === 'suspended') ctx.resume();
      return ctx;
    }

    function warm(){
      // small silent warm-up to settle audio pipeline
      const c = ensureCtx();
      const dur = 0.06; // 60ms
      const buf = c.createBuffer(1, Math.max(1, Math.floor(c.sampleRate * dur)), c.sampleRate);
      const src = c.createBufferSource();
      src.buffer = buf; src.connect(c.destination);
      const when = c.currentTime + 0.02;
      try { src.start(when); } catch {}
    }

    function connect(){
      document.getElementById('s').textContent = 'Connecting...';
      es = new EventSource('/events');
      es.onopen = () => { document.getElementById('s').textContent = 'Connected'; ensureCtx(); warm(); };
      es.onerror = () => { document.getElementById('s').textContent = 'Disconnected (retrying)'; };
      es.onmessage = ev => {
        if (!ev.data) return;
        try {
          const m = JSON.parse(ev.data);
          if (m.type === 'audio') { q.push(m.data); if (!playing) playNext(); }
        } catch {}
      };
    }

    function b64ToBytes(b64){
      const bin = atob(b64); const len = bin.length; const out = new Uint8Array(len);
      for (let i=0;i<len;i++) out[i]=bin.charCodeAt(i); return out;
    }

    function playNext(){
      if (playing || q.length===0) return; playing = true;
      const c = ensureCtx();
      const bytes = b64ToBytes(q.shift());
      const ab = bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
      c.decodeAudioData(ab.slice(0)).then(buf => {
        const src = c.createBufferSource(); src.buffer = buf; src.connect(c.destination);
        const when = Math.max(c.currentTime + START_OFFSET, c.currentTime + 0.02);
        try { src.start(when); } catch {}
        src.onended = () => { playing=false; playNext(); };
      }).catch(() => { playing=false; playNext(); });
    }

    window.addEventListener('load', connect);
  </script>
  </head>
  <body>
    <div id=\"s\">Loading...</div>
  </body>
  </html>
"""


# ---------------- Audio helpers ----------------
def _normalize_to_float_mono(samples: np.ndarray) -> np.ndarray:
    if not isinstance(samples, np.ndarray):
        samples = np.asarray(samples)
    if samples.ndim == 2:
        samples = samples.mean(axis=1)
    s = samples.astype(np.float32, copy=False)
    s = np.clip(s, -1.0, 1.0)
    return s


def _apply_preroll_and_fade(samples: np.ndarray, sr: int, preroll_ms: float = 40.0, fade_ms: float = 8.0) -> np.ndarray:
    """Add a short silent pre-roll and a quick fade-in to reduce initial choppiness.
    Both values are small enough to be imperceptible while stabilizing playback.
    """
    s = _normalize_to_float_mono(samples)
    # Pre-roll silence
    n_pre = max(0, int(sr * (preroll_ms / 1000.0)))
    if n_pre:
        s = np.concatenate([np.zeros(n_pre, dtype=np.float32), s])
    # Short fade-in ramp
    n_fade = max(1, int(sr * (fade_ms / 1000.0)))
    ramp = np.linspace(0.0, 1.0, num=n_fade, dtype=np.float32)
    s[:n_fade] *= ramp
    return s


def _encode_wav_bytes(samples: np.ndarray, sample_rate: int) -> bytes:
    s = _apply_preroll_and_fade(samples, sample_rate)
    pcm16 = (np.clip(s, -1.0, 1.0) * 32767.0).astype("<i2")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm16.tobytes())
    return buf.getvalue()


# ---------------- Broadcast core ----------------
async def _broadcast_json(obj: dict):
    if not _client_queues:
        return
    line = f"data: {__import__('json').dumps(obj, separators=(',',':'))}\n\n"
    stale: List[asyncio.Queue] = []
    for q in list(_client_queues):
        try:
            q.put_nowait(line)
        except asyncio.QueueFull:
            stale.append(q)
    for q in stale:
        _client_queues.discard(q)


def send_audio_to_obs(samples: np.ndarray, sample_rate: int):
    global _loop
    if _loop is None or not _loop.is_running():
        LOGGER.debug("server2 not running; dropping audio")
        return
    try:
        wav = _encode_wav_bytes(samples, sample_rate)
        b64 = base64.b64encode(wav).decode("ascii")
        asyncio.run_coroutine_threadsafe(_broadcast_json({"type": "audio", "data": b64}), _loop)
    except Exception:
        LOGGER.exception("send_audio_to_obs failed")


def send_wav_bytes_to_obs(wav_bytes: bytes):
    global _loop
    if _loop is None or not _loop.is_running():
        LOGGER.debug("server2 not running; dropping wav bytes")
        return
    try:
        b64 = base64.b64encode(wav_bytes).decode("ascii")
        asyncio.run_coroutine_threadsafe(_broadcast_json({"type": "audio", "data": b64}), _loop)
    except Exception:
        LOGGER.exception("send_wav_bytes_to_obs failed")


# ---------------- HTTP handlers ----------------
async def _root(_: web.Request):
    return web.Response(text=_HTML, content_type="text/html", headers={"Cache-Control": "no-store"})


async def _events(request: web.Request):
    q: asyncio.Queue = asyncio.Queue(maxsize=100)
    _client_queues.add(q)
    resp = web.StreamResponse(
        status=200,
        headers={
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-store",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )
    await resp.prepare(request)
    await resp.write(b": ok\n\n")
    try:
        while True:
            try:
                line = await asyncio.wait_for(q.get(), timeout=15.0)
                await resp.write(line.encode("utf-8"))
            except asyncio.TimeoutError:
                await resp.write(b"data:{\"type\":\"ping\"}\n\n")
            await resp.drain()
    except (asyncio.CancelledError, ConnectionResetError, BrokenPipeError):
        pass
    finally:
        _client_queues.discard(q)
    return resp


# ---------------- Lifecycle ----------------
async def _async_start(host: str, port: int):
    global _app, _runner, _site
    _app = web.Application()
    _app.router.add_get("/", _root)
    _app.router.add_get("/events", _events)

    _runner = web.AppRunner(_app)
    await _runner.setup()
    _site = web.TCPSite(_runner, host, port)
    await _site.start()
    LOGGER.info("server2 listening on http://%s:%d", host if host != "0.0.0.0" else "localhost", port)
    _ready.set()
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass


def _thread_main(host: str, port: int):
    global _loop
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)
    try:
        _loop.run_until_complete(_async_start(host, port))
    except Exception:
        LOGGER.exception("server2 crashed")
    finally:
        _loop.close()


def start(host: str = HOST, http_port: int = HTTP_PORT):
    global _started
    with _lock:
        if _started:
            LOGGER.info("server2 already started")
            return
        _started = True
    threading.Thread(target=_thread_main, args=(host, http_port), name="SSE-Audio-Server2", daemon=True).start()
    if not _ready.wait(timeout=5):
        LOGGER.warning("server2 start timeout (may still initialize)")
    else:
        LOGGER.info("server2 ready")


def stop():
    global _loop
    if _loop and _loop.is_running():
        _loop.call_soon_threadsafe(_loop.stop)

