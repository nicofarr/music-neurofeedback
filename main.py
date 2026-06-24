import asyncio
import webbrowser
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

# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)