#!/usr/bin/env python3
"""
Send SKILL commands to CIW to:
1. Close blocking dialogs (Loading State / Choose Design)
2. Open Viva waveform viewer on the TM14 PSF database
"""
import ctypes, time, os, subprocess, sys

os.environ['DISPLAY'] = ':0'
xlib = ctypes.cdll.LoadLibrary('libX11.so.6')
xtst = ctypes.cdll.LoadLibrary('libXtst.so.6')

xlib.XOpenDisplay.restype  = ctypes.c_void_p
xlib.XOpenDisplay.argtypes = [ctypes.c_char_p]
xlib.XRaiseWindow.restype  = ctypes.c_int
xlib.XRaiseWindow.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
xlib.XFlush.restype        = ctypes.c_int
xlib.XFlush.argtypes       = [ctypes.c_void_p]
xlib.XCloseDisplay.restype  = ctypes.c_int
xlib.XCloseDisplay.argtypes = [ctypes.c_void_p]
xlib.XKeysymToKeycode.restype  = ctypes.c_uint
xlib.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]

xtst.XTestFakeMotionEvent.restype  = ctypes.c_int
xtst.XTestFakeMotionEvent.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_ulong]
xtst.XTestFakeButtonEvent.restype  = ctypes.c_int
xtst.XTestFakeButtonEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_bool, ctypes.c_ulong]
xtst.XTestFakeKeyEvent.restype  = ctypes.c_int
xtst.XTestFakeKeyEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_bool, ctypes.c_ulong]

display = xlib.XOpenDisplay(b':0')
if not display:
    sys.exit(1)

XK_Return  = ctypes.c_ulong(0xFF0D)
XK_Shift_L = ctypes.c_ulong(0xFFE1)
enter_code = xlib.XKeysymToKeycode(display, XK_Return)
shift_code = xlib.XKeysymToKeycode(display, XK_Shift_L)

SHIFT_CHARS = set('"<>?:{}|~!@#$%^&*()_+ABCDEFGHIJKLMNOPQRSTUVWXYZ')
KEYSYM_MAP = {c: ord(c) for c in 'abcdefghijklmnopqrstuvwxyz0123456789 !"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'}
for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
    KEYSYM_MAP[c] = ord(c)

CIW_WIN = 0x2e00008
# CIW geometry: 707x321 at position +1139+792
# Click in the command input area (bottom of CIW)
CIW_X = 1139 + 350
CIW_Y = 792 + 295

def click_at(x, y):
    xtst.XTestFakeMotionEvent(display, -1, x, y, ctypes.c_ulong(0))
    xlib.XFlush(display)
    time.sleep(0.15)
    xtst.XTestFakeButtonEvent(display, 1, True,  ctypes.c_ulong(0))
    xlib.XFlush(display)
    time.sleep(0.08)
    xtst.XTestFakeButtonEvent(display, 1, False, ctypes.c_ulong(0))
    xlib.XFlush(display)
    time.sleep(0.2)

def type_char(ch):
    if ch not in KEYSYM_MAP:
        return
    kc = xlib.XKeysymToKeycode(display, ctypes.c_ulong(KEYSYM_MAP[ch]))
    if kc == 0:
        return
    need_shift = ch in SHIFT_CHARS
    if need_shift:
        xtst.XTestFakeKeyEvent(display, shift_code, True,  ctypes.c_ulong(0))
        time.sleep(0.005)
    xtst.XTestFakeKeyEvent(display, kc, True,  ctypes.c_ulong(0))
    time.sleep(0.012)
    xtst.XTestFakeKeyEvent(display, kc, False, ctypes.c_ulong(0))
    time.sleep(0.012)
    if need_shift:
        xtst.XTestFakeKeyEvent(display, shift_code, False, ctypes.c_ulong(0))
        time.sleep(0.005)

def press_enter():
    xtst.XTestFakeKeyEvent(display, enter_code, True,  ctypes.c_ulong(0))
    xlib.XFlush(display)
    time.sleep(0.05)
    xtst.XTestFakeKeyEvent(display, enter_code, False, ctypes.c_ulong(0))
    xlib.XFlush(display)
    time.sleep(0.35)

def type_cmd(text, wait=0.5):
    print(f'  CIW>>> {text}')
    for ch in text:
        type_char(ch)
    xlib.XFlush(display)
    time.sleep(0.2)
    press_enter()
    time.sleep(wait)

# Focus CIW
xlib.XRaiseWindow(display, ctypes.c_ulong(CIW_WIN))
xlib.XFlush(display)
time.sleep(0.5)
click_at(CIW_X, CIW_Y)
time.sleep(0.5)

print("=== Step 1: Close blocking dialogs via SKILL ===")
# hiDeleteWindow will close any blocking non-main window
skill_close = 'mapcar( lambda((w) let((t hiGetWindowTitle(w)) if(t && (nindex(t "Loading") || nindex(t "Choose") || nindex(t "Session") || nindex(t "Setup")) then hiDeleteWindow(w)))) hiGetWindowList())'
type_cmd(skill_close, wait=1.5)

# Check remaining
res = subprocess.run(["xwininfo", "-root", "-tree"],
                     env={"DISPLAY": ":0", "HOME": "/home/lary"},
                     capture_output=True, text=True)
still = [l for l in res.stdout.splitlines() if "Loading State" in l or "Choose Design" in l]
print(f"Still blocking: {len(still)} dialog(s)")
for s in still:
    print(f"  {s.strip()}")

print("\n=== Step 2: Triggering ADE L RUN button via SKILL ===")
type_cmd('mapcar(lambda((w) let((s) s=sevSession(w) if(s then sevNetlistAndRun(s)))) hiGetWindowList())', wait=40.0)

print("\n=== Step 3: Open waveform image ===")
type_cmd('bvImg("/home/lary/project/BVU025/SCH/cosim/pattern/TM14/images/cosim_waveform.png")', wait=1.0)

xlib.XCloseDisplay(display)
print("\nDone!")
