import asyncio
import webbrowser
import subprocess
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pythonosc.udp_client import SimpleUDPClient

from EEG import EEG_signal_processing

# ── EEG ───────────────────────────────────────────────────────────────────────
signal = EEG_signal_processing()
# signal.start()

HOST = "127.0.0.1"
PORT = 9000
BASE = "/reverb"

player_process = None
player_running = False

def send(key, value):
    try:
        SimpleUDPClient(HOST, PORT).send_message(f"{BASE}/{key}", float(value))
    except Exception as e:
        print(f"OSC error: {e}")

# ── App ───────────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    webbrowser.open("http://127.0.0.1:8000")
    yield

app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="."), name="static")

@app.get("/")
def index():
    return FileResponse("index.html")

# ── WebSocket EEG ─────────────────────────────────────────────────────────────
@app.websocket("/ws/eeg")
async def eeg_ws(websocket: WebSocket):
    global player_running
    
    await websocket.accept()
    try:
        while True:
            alpha = signal.alpha
            beta  = signal.beta
            ratio = signal.smoothed_ratio

            await websocket.send_json({
                "alpha": alpha,
                "beta":  beta,
                "ratio": ratio,
                "ref_ready": signal.ref_ready,
                "player_running": player_process is not None and player_process.poll() is None and player_running,
                "eeg_amplitudes": signal.eeg_amplitudes.tolist() if hasattr(signal, 'eeg_amplitudes') else [0]*6,
            })
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        pass

# ── OSC endpoints ─────────────────────────────────────────────────────────────
from fastapi import Body

@app.post("/osc/{key}")
def osc_send(key: str, value: float = Body(..., embed=True)):
    if key == "smoothing":
        signal.smoothing = float(value)
    else:
        send(key, value)
    return {"ok": True}

@app.post("/save")
def save():
    signal.save_data()
    return {"ok": True}

@app.post("/start")
def start():
    signal.start()
    return {"ok": True}

@app.post("/stop")
def stop():
    signal.stop()
    return {"ok": True}

@app.post("/baseline")
def set_baseline(moving: bool = Body(..., embed=True)):
    signal.moving_baseline = moving
    return {"ok": True}

# ── OSC endpoints ──────────────────────────────────────────────────────────────────
@app.post("/player/start")
def player_start(source_a: str = Body(..., embed=True), source_b: str = Body(..., embed=True)):
    global player_process, player_running
    if player_process and player_process.poll() is None:
        player_process.kill()  
    player_process = subprocess.Popen([sys.executable, "player.py", source_a, source_b])
    player_running = True
    return {"ok": True}

@app.post("/player/stop")
def player_stop():
    global player_process, player_running
    if player_process and player_process.poll() is None:
        player_process.kill()
    player_running = False
    return {"ok": True}

@app.post("/player/pause")
def player_pause():
    global player_running
    player_running = False
    send("paused", 1.0)
    return {"ok": True}

@app.post("/player/resume")
def player_resume():
    global player_running
    player_running = True
    send("paused", 0.0)
    return {"ok": True}

# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)