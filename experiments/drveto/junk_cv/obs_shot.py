#!/usr/bin/env python3
"""
Grab one screenshot of the current OBS program scene via the obs-websocket v5 API.

Used to capture clean 4K HDMI frames of a MiSTer NES game for read_board.py.
This SIDESTEPS two capture traps: the capture card is single-consumer (OBS holds
/dev/video0, so it can't be ffmpeg'd), and the growing OBS .mkv defeats `-sseof`
(lands at file start on a growing MKV -- see memory dr-mario-cvc-video-instrument).

Credential comes from the env var OBS_WS_PASSWORD (set it in your local, gitignored
setenv.sh). Never hard-code it. Host/port default to a local OBS (127.0.0.1:4455).

Usage:  OBS_WS_PASSWORD=... python3 obs_shot.py out.png
"""
import sys, os, json, base64, hashlib
from websocket import create_connection   # pip/uv install websocket-client

PW = os.environ.get("OBS_WS_PASSWORD", "")
HOST = os.environ.get("OBS_WS_HOST", "127.0.0.1")
PORT = os.environ.get("OBS_WS_PORT", "4455")
OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/obs_shot.png"

ws = create_connection(f"ws://{HOST}:{PORT}", timeout=10)
hello = json.loads(ws.recv())                       # op 0 Hello
auth = hello["d"].get("authentication")
ident = {"op": 1, "d": {"rpcVersion": 1}}
if auth:
    if not PW:
        sys.exit("OBS requires auth but OBS_WS_PASSWORD is not set")
    secret = base64.b64encode(hashlib.sha256((PW + auth["salt"]).encode()).digest()).decode()
    resp = base64.b64encode(hashlib.sha256((secret + auth["challenge"]).encode()).digest()).decode()
    ident["d"]["authentication"] = resp
ws.send(json.dumps(ident))
json.loads(ws.recv())                               # op 2 Identified

def req(t, d, rid):
    ws.send(json.dumps({"op": 6, "d": {"requestType": t, "requestId": rid, "requestData": d}}))
    while True:
        m = json.loads(ws.recv())
        if m["op"] == 7 and m["d"]["requestId"] == rid:
            return m["d"]

scene = req("GetCurrentProgramScene", {}, "s")["responseData"]
name = scene.get("currentProgramSceneName") or scene.get("sceneName")
r = req("SaveSourceScreenshot",
        {"sourceName": name, "imageFormat": "png", "imageFilePath": OUT}, "shot")
print("scene:", name, "| ok:", r["requestStatus"]["result"], "|", OUT)
ws.close()
