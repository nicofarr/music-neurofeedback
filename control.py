#!/usr/bin/env python3
"""
Streamlit OSC controller for player.py — all reverb parameters.

Install:  pip install streamlit python-osc
Run:      streamlit run control.py
"""

import streamlit as st
from pythonosc.udp_client import SimpleUDPClient

st.set_page_config(page_title="Reverb Control", page_icon="🎛️", layout="centered")

st.title("🎛️  Reverb Controller")
st.caption("All sliders send OSC to `player.py` on every change")

# ── Connection ────────────────────────────────────────────────────────────────
with st.expander("⚙️  Connection", expanded=False):
    c1, c2, c3 = st.columns([3, 1, 2])
    host = c1.text_input("Host", "127.0.0.1")
    port = int(c2.number_input("Port", 1, 65535, 9000))
    base = c3.text_input("Base address", "/reverb")

def send(key, value):
    try:
        SimpleUDPClient(host, port).send_message(f"{base}/{key}", float(value))
    except Exception as e:
        st.sidebar.error(f"OSC error: {e}")

st.divider()

# ── Presets ───────────────────────────────────────────────────────────────────
PRESETS = {
    "Dry":      dict(room_size=0.1, damping=0.9, wet_level=0.0,  dry_level=1.0,  width=1.0, freeze_mode=0.0),
    "Room":     dict(room_size=0.3, damping=0.6, wet_level=0.25, dry_level=0.8,  width=0.7, freeze_mode=0.0),
    "Hall":     dict(room_size=0.6, damping=0.4, wet_level=0.4,  dry_level=0.7,  width=1.0, freeze_mode=0.0),
    "Cathedral":dict(room_size=0.9, damping=0.1, wet_level=0.6,  dry_level=0.5,  width=1.0, freeze_mode=0.0),
    "Infinite": dict(room_size=1.0, damping=0.0, wet_level=0.8,  dry_level=0.3,  width=1.0, freeze_mode=1.0),
}

cols = st.columns(len(PRESETS))
for col, (name, preset) in zip(cols, PRESETS.items()):
    if col.button(name, use_container_width=True):
        st.session_state.update(preset)
        for k, v in preset.items():
            send(k, v)

st.divider()

# ── Levels ────────────────────────────────────────────────────────────────────
st.subheader("Levels")
lc1, lc2 = st.columns(2)

wet_level = lc1.slider(
    "Wet level", 0.0, 1.0,
    st.session_state.get("wet_level", 0.33), step=0.01, key="wet_level",
    help="Amount of reverb signal in the output",
)
dry_level = lc2.slider(
    "Dry level", 0.0, 1.0,
    st.session_state.get("dry_level", 0.4), step=0.01, key="dry_level",
    help="Amount of original (dry) signal in the output",
)

send("wet_level", wet_level)
send("dry_level", dry_level)

# ── Character ─────────────────────────────────────────────────────────────────
st.subheader("Character")
cc1, cc2 = st.columns(2)

room_size = cc1.slider(
    "Room size", 0.0, 1.0,
    st.session_state.get("room_size", 0.5), step=0.01, key="room_size",
    help="Size of the virtual room — larger = longer reverb tail",
)
damping = cc2.slider(
    "Damping", 0.0, 1.0,
    st.session_state.get("damping", 0.5), step=0.01, key="damping",
    help="High-frequency absorption — higher = darker, shorter tail",
)

width = cc1.slider(
    "Width", 0.0, 1.0,
    st.session_state.get("width", 1.0), step=0.01, key="width",
    help="Stereo width of the reverb",
)
freeze_mode = cc2.slider(
    "Freeze mode", 0.0, 1.0,
    st.session_state.get("freeze_mode", 0.0), step=0.01, key="freeze_mode",
    help="Freeze reverb tail (1.0 = infinite sustain, no new input)",
)

send("room_size", room_size)
send("damping",   damping)
send("width",     width)
send("freeze_mode", freeze_mode)

# ── Status ────────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    f"Sending to `{host}:{port}` — addresses: "
    + "  |  ".join(f"`{base}/{k}`" for k in
                   ["wet_level","dry_level","room_size","damping","width","freeze_mode"])
)
