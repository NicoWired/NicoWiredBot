# WARNING:
# This file has been entirely vibe coded. I didn't write a single line, and I have no idea how antyhing here works.
# I'm hoping to replace all of this fot twitchio's overlay system once it's implemented.

import asyncio
import base64
import io
import logging
import threading
import wave
from typing import List, Set
import urllib.parse

import numpy as np
from aiohttp import web

LOGGER = logging.getLogger("Server")

_HOST = "0.0.0.0"
_HTTP_PORT = 8080

# Each connected SSE client gets its own asyncio.Queue of event payload strings
_client_queues: Set[asyncio.Queue] = set()

_server_loop: asyncio.AbstractEventLoop | None = None
_app: web.Application | None = None
_runner: web.AppRunner | None = None
_site: web.TCPSite | None = None

_started = False
_lock = threading.Lock()
_ready_event = threading.Event()


_HTML_PAGE = """<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<title>NicoWiredBot TTS Audio (SSE)</title>
<style>
  body { background:#111; color:#eee; font-family:sans-serif; margin:0; padding:12px;}
  #status { margin:4px 0; padding:4px 8px; background:#222; display:inline-block; font-size:13px; }
  #log { white-space:pre-wrap; font-size:11px; background:#1d1d1d; padding:8px; max-height:200px; overflow:auto; margin-top:8px; }
  #queue { position:fixed; top:6px; right:8px; background:#222; padding:4px 8px; border-radius:4px; font-size:12px; }
  #unlock { display:none; margin:8px 0; padding:8px 14px; font-size:14px; background:#444; color:#fff; border:1px solid #666; cursor:pointer; }
  button { margin:4px 4px 0 0; }
  .error { color:#f55; }
</style>
</head>
<body>
<h3 style="margin:0 0 6px 0;">NicoWiredBot TTS Audio Bridge (SSE)</h3>
<div id="status">Loading...</div>
<div id="queue">Queue: 0</div>
<div>
  <button onclick="triggerTest()">Server Test Tone</button>
  <button onclick="clearLog()">Clear Log</button>
</div>
<button id="unlock" onclick="unlockAudio()">Unlock Audio (Click if muted)</button>
<div id="log"></div>
<script>
const statusEl = document.getElementById('status');
const logEl = document.getElementById('log');
const unlockBtn = document.getElementById('unlock');
const queueEl = document.getElementById('queue');

let es;
let audioCtx = null;
let playing = false;
let queue = [];
let connected = false;
let lastError = null;
let warmed = false;          // <--- added
const START_OFFSET = 0.03;   // slight scheduling offset (seconds)

function log(msg, cls){
  const t=new Date().toISOString().split('T')[1].replace('Z','');
  const line = document.createElement('div');
  line.textContent = '['+t+'] '+msg;
  if (cls) line.className = cls;
  logEl.appendChild(line);
  logEl.scrollTop = logEl.scrollHeight;
  console.log('[NW TTS]', msg);
}
function clearLog(){ logEl.textContent=''; }
function updateQueue(){ queueEl.textContent = 'Queue: '+queue.length; }

function ensureCtx(){
  if(!audioCtx){
    const AC = window.AudioContext || window.webkitAudioContext;
    if(!AC){
      log('No AudioContext support', 'error');
      return null;
    }
    audioCtx = new AC({ latencyHint:'interactive' });
  }
  if(audioCtx.state === 'suspended'){
    audioCtx.resume().catch(e=>log('Resume failed: '+e,'error'));
  }
  return audioCtx;
}

// Warm-up: play a short silent buffer once so first real audio is clean
function warmAudio(){
  if (warmed) return;
  const ctx = ensureCtx();
  if(!ctx) return;
  try {
    const dur = 0.08;
    const buf = ctx.createBuffer(1, Math.max(1, Math.floor(ctx.sampleRate * dur)), ctx.sampleRate);
    const src = ctx.createBufferSource();
    src.buffer = buf;
    src.connect(ctx.destination);
    // schedule slightly ahead to avoid truncation
    const when = ctx.currentTime + 0.01;
    src.start(when);
    warmed = true;
    log('Audio warm-up sent');
  } catch(e){
    log('Warm-up failed: '+e, 'error');
  }
}

function unlockAudio(){
  const ctx = ensureCtx();
  if(!ctx) return;
  const osc = ctx.createOscillator();
  osc.frequency.value = 1;
  osc.connect(ctx.destination);
  try { osc.start(); osc.stop(ctx.currentTime + 0.03); } catch{}
  setTimeout(()=>{ if(ctx.state === 'running'){ unlockBtn.style.display='none'; log('Audio unlocked'); }}, 80);
}

function connectSSE(){
  statusEl.textContent='Connecting...';
  es = new EventSource('/events');
  es.onopen = () => {
    connected = true;
    statusEl.textContent='Connected';
    log('SSE open');
    ensureCtx();
    warmAudio();   // <--- warm immediately on connect
    reportUA();
  };
  es.onerror = (e) => {
    statusEl.textContent='Disconnected (retrying)';
    if(connected){
      log('SSE disconnected; retrying...');
    }
    connected = false;
  };
  es.onmessage = ev => {
    if(!ev.data) return;
    try {
      const msg = JSON.parse(ev.data);
      if(msg.type === 'audio'){
        queue.push(msg.data);
        updateQueue();
        log('Audio queued. Length='+queue.length);
        if(!playing){
          // if not warmed yet (edge race), ensure
          warmAudio();
          playNext();
        }
      } else if(msg.type === 'ping'){
        // heartbeat
      } else {
        log('Unknown event type: '+msg.type);
      }
    } catch(err){
      log('Parse error: '+err, 'error');
    }
  };
}

async function playNext(){
  if(playing || queue.length === 0) return;
  playing = true;
  const b64 = queue.shift();
  updateQueue();
  try{
    const ctx = ensureCtx();
    if(!ctx){
      log('No AudioContext; skipping.', 'error');
      playing = false;
      return;
    }
    const wavBytes = base64ToBytes(b64);
    const arrayBuf = wavBytes.buffer.slice(wavBytes.byteOffset, wavBytes.byteOffset + wavBytes.byteLength);
    ctx.decodeAudioData(arrayBuf.slice(0), decoded => {
      try {
        const src = ctx.createBufferSource();
        src.buffer = decoded;
        src.connect(ctx.destination);
        const when = Math.max(ctx.currentTime + START_OFFSET, ctx.currentTime + 0.005);
        src.start(when);
        log('Started clip ('+decoded.duration.toFixed(2)+'s) @+'+(when-ctx.currentTime).toFixed(3)+'s');
        src.onended = () => {
          playing = false;
          playNext();
        };
      } catch(e){
        log('Start failed: '+e, 'error');
        playing = false;
        fallbackTagPlay(b64);
      }
    }, err => {
      log('decodeAudioData failed: '+err+'. Falling back <audio>', 'error');
      fallbackTagPlay(b64);
    });
  }catch(e){
    log('Playback error: '+e, 'error');
    fallbackTagPlay(b64);
  }
}

function fallbackTagPlay(b64){
  try{
    const bin = atob(b64);
    const len = bin.length;
    const bytes = new Uint8Array(len);
    for(let i=0;i<len;i++) bytes[i]=bin.charCodeAt(i);
    const blob = new Blob([bytes], {type:'audio/wav'});
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    audio.autoplay = true;
    audio.volume = 1.0;
    audio.play().then(()=>{
      log('Fallback <audio> playing.');
    }).catch(err=>{
      log('Fallback play blocked: '+err, 'error');
      unlockBtn.style.display='inline-block';
    });
    audio.onended = () => {
      URL.revokeObjectURL(url);
      playing = false;
      playNext();
    };
  }catch(err){
    log('Fallback exception: '+err, 'error');
    playing = false;
    playNext();
  }
}

function base64ToBytes(b64){
  const bin = atob(b64);
  const len = bin.length;
  const bytes = new Uint8Array(len);
  for(let i=0;i<len;i++) bytes[i]=bin.charCodeAt(i);
  return bytes;
}

function triggerTest(){
  fetch('/test-tone').then(r=>r.json()).then(j=>log('Test tone '+j.status)).catch(e=>log('Test tone error '+e,'error'));
}

function reportUA(){
  try{
    const ua = encodeURIComponent(navigator.userAgent);
    const img = new Image();
    img.src = '/ua?ua='+ua+'&t='+Date.now();
  }catch(e){}
}

connectSSE();
setInterval(()=>{ if(!playing) playNext(); }, 1500);
</script>
</body>
</html>
"""

# -------- Audio Helpers --------

def _normalize_to_float_mono(samples: np.ndarray) -> np.ndarray:
    if not isinstance(samples, np.ndarray):
        samples = np.asarray(samples)
    if samples.ndim == 2:
        samples = samples.mean(axis=1)
    samples = samples.squeeze()
    samples = samples.astype(np.float32)
    peak = float(np.max(np.abs(samples))) if samples.size else 1.0
    if peak > 1.0:
        samples = samples / peak
    return np.clip(samples, -1.0, 1.0)

def _encode_wav_bytes(samples: np.ndarray, sample_rate: int) -> bytes:
    s = _normalize_to_float_mono(samples)
    pcm16 = (s * 32767.0).astype("<i2")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm16.tobytes())
    return buf.getvalue()

# -------- Broadcast Core --------

async def _broadcast_json(obj: dict):
    if not _client_queues:
        LOGGER.debug("No SSE clients; skip broadcast.")
        return
    data_line = f"data: {__import__('json').dumps(obj, separators=(',',':'))}\n\n"
    stale: List[asyncio.Queue] = []
    for q in list(_client_queues):
        try:
            q.put_nowait(data_line)
        except asyncio.QueueFull:
            LOGGER.warning("Client queue full; removing client.")
            stale.append(q)
    for q in stale:
        _client_queues.discard(q)
    LOGGER.info("Queued event '%s' to %d clients.", obj.get("type"), len(_client_queues))

def send_audio_to_obs(samples: np.ndarray, sample_rate: int):
    global _server_loop
    if _server_loop is None or not _server_loop.is_running():
        LOGGER.warning("send_audio_to_obs called but server not running.")
        return
    try:
        wav = _encode_wav_bytes(samples, sample_rate)
        b64 = base64.b64encode(wav).decode("ascii")
        asyncio.run_coroutine_threadsafe(_broadcast_json({"type": "audio", "data": b64}), _server_loop)
        LOGGER.debug("Audio scheduled (%.2f sec approx).", len(wav)/ (sample_rate*2))
    except Exception as e:
        LOGGER.exception("send_audio_to_obs failed: %s", e)

def send_wav_bytes_to_obs(wav_bytes: bytes):
    global _server_loop
    if _server_loop is None or not _server_loop.is_running():
        LOGGER.warning("send_wav_bytes_to_obs called but server not running.")
        return
    try:
        b64 = base64.b64encode(wav_bytes).decode("ascii")
        asyncio.run_coroutine_threadsafe(_broadcast_json({"type": "audio", "data": b64}), _server_loop)
    except Exception as e:
        LOGGER.exception("send_wav_bytes_to_obs failed: %s", e)

# -------- Test Tone / Inject --------

async def _test_tone():
    sr = 22050
    t = np.linspace(0, 0.35, int(sr * 0.35), endpoint=False)
    samples = 0.35 * np.sin(2 * np.pi * 880 * t) * np.hanning(len(t))
    await _broadcast_json({"type": "audio", "data": base64.b64encode(_encode_wav_bytes(samples, sr)).decode("ascii")})

def test_tone():
    if _server_loop and _server_loop.is_running():
        asyncio.run_coroutine_threadsafe(_test_tone(), _server_loop)
    else:
        LOGGER.warning("test_tone: server not running.")

async def _inject_tts(text: str):
    # Simple synthetic beep pattern based on text length (debug helper)
    sr = 22050
    length = max(1, min(len(text), 40))
    dur = 0.15 + 0.015 * length
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    freq = 440 + (length % 10) * 30
    samples = 0.28 * np.sin(2 * np.pi * freq * t) * np.hanning(len(t))
    await _broadcast_json({"type": "audio", "data": base64.b64encode(_encode_wav_bytes(samples, sr)).decode("ascii")})

# -------- HTTP Handlers --------

async def _root(request: web.Request):
    return web.Response(body=_HTML_PAGE, content_type="text/html", headers={"Cache-Control": "no-store"})

async def _test_tone_route(request: web.Request):
    asyncio.create_task(_test_tone())
    return web.json_response({"status": "queued"})

async def _inject_route(request: web.Request):
    txt = request.query.get("text", "test")
    asyncio.create_task(_inject_tts(txt))
    return web.json_response({"status": "queued", "text": txt})

async def _ping(request: web.Request):
    return web.json_response({"status": "ok"})

async def _ua_pixel(request: web.Request):
    ua = request.query.get("ua", "")
    if ua:
        ua_dec = urllib.parse.unquote_plus(ua)
        LOGGER.info("UA: %s", ua_dec)
    # 1x1 transparent gif
    return web.Response(
        body=b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xFF\xFF\xFF!\xF9\x04\x01\x00\x00\x00\x00,\x00\x00"
             b"\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;",
        content_type="image/gif",
        headers={"Cache-Control": "no-store"}
    )

async def _events(request: web.Request):
    """
    SSE endpoint. Keeps a streaming response open and pushes data lines.
    """
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    _client_queues.add(queue)
    LOGGER.info("SSE client connected (total=%d)", len(_client_queues))

    resp = web.StreamResponse(
        status=200,
        reason='OK',
        headers={
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-store",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )
    await resp.prepare(request)
    # Initial comment / kick
    await resp.write(b": connected\n\n")

    try:
        while True:
            try:
                line = await asyncio.wait_for(queue.get(), timeout=15.0)
                await resp.write(line.encode("utf-8"))
            except asyncio.TimeoutError:
                # heartbeat
                await resp.write(b"data:{\"type\":\"ping\"}\n\n");
            await resp.drain()
    except (asyncio.CancelledError, ConnectionResetError, BrokenPipeError):
        pass
    finally:
        _client_queues.discard(queue)
        LOGGER.info("SSE client disconnected (total=%d)", len(_client_queues))
    return resp

# -------- Server Lifecycle --------

async def _async_start(host: str, port: int):
    global _app, _runner, _site
    _app = web.Application()
    _app.router.add_get("/", _root)
    _app.router.add_get("/events", _events)
    _app.router.add_get("/test-tone", _test_tone_route)
    _app.router.add_get("/inject", _inject_route)
    _app.router.add_get("/ping", _ping)
    _app.router.add_get("/ua", _ua_pixel)

    _runner = web.AppRunner(_app)
    await _runner.setup()
    _site = web.TCPSite(_runner, host, port)
    await _site.start()
    LOGGER.info("HTTP(SSE) server listening on http://%s:%d", host if host != "0.0.0.0" else "localhost", port)
    _ready_event.set()

    # Keep loop alive
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass

def _thread_main(host: str, port: int):
    global _server_loop
    _server_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_server_loop)
    try:
        _server_loop.run_until_complete(_async_start(host, port))
    except Exception as e:
        LOGGER.exception("Server crashed: %s", e)
    finally:
        _server_loop.close()
        LOGGER.info("Server loop closed.")

def start(host: str = _HOST, http_port: int = _HTTP_PORT):
    global _started
    with _lock:
        if _started:
            LOGGER.info("Server already started.")
            return
        _started = True
    threading.Thread(
        target=_thread_main,
        args=(host, http_port),
        name="SSE-Audio-Server",
        daemon=True,
    ).start()
    if not _ready_event.wait(timeout=5):
        LOGGER.warning("Server start timeout (may still initialize).")
    else:
        LOGGER.info("Server ready.")

def stop():
    global _server_loop
    if _server_loop and _server_loop.is_running():
        _server_loop.call_soon_threadsafe(_server_loop.stop)