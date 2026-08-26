#!/usr/bin/env python3
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

XK_Return    = ctypes.c_ulong(0xFF0D)
XK_BackSpace = ctypes.c_ulong(0xFF08)
XK_Escape    = ctypes.c_ulong(0xFF1B)
XK_Control_L = ctypes.c_ulong(0xFFE3)
XK_Shift_L   = ctypes.c_ulong(0xFFE1)
XK_u         = ctypes.c_ulong(0x0075)

enter_code = xlib.XKeysymToKeycode(display, XK_Return)
bs_code    = xlib.XKeysymToKeycode(display, XK_BackSpace)
esc_code   = xlib.XKeysymToKeycode(display, XK_Escape)
ctrl_code  = xlib.XKeysymToKeycode(display, XK_Control_L)
shift_code = xlib.XKeysymToKeycode(display, XK_Shift_L)
u_code     = xlib.XKeysymToKeycode(display, XK_u)

SHIFT_CHARS = set('"<>?:{}|~!@#$%^&*()_+ABCDEFGHIJKLMNOPQRSTUVWXYZ')
KEYSYM_MAP = {c: ord(c) for c in 'abcdefghijklmnopqrstuvwxyz0123456789 !"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'}
for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
    KEYSYM_MAP[c] = ord(c)

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

def press_key(kc, shift=False, ctrl=False):
    if ctrl:  xtst.XTestFakeKeyEvent(display, ctrl_code, True, ctypes.c_ulong(0))
    if shift: xtst.XTestFakeKeyEvent(display, shift_code, True, ctypes.c_ulong(0))
    time.sleep(0.01)
    xtst.XTestFakeKeyEvent(display, kc, True, ctypes.c_ulong(0))
    time.sleep(0.01)
    xtst.XTestFakeKeyEvent(display, kc, False, ctypes.c_ulong(0))
    time.sleep(0.01)
    if shift: xtst.XTestFakeKeyEvent(display, shift_code, False, ctypes.c_ulong(0))
    if ctrl:  xtst.XTestFakeKeyEvent(display, ctrl_code, False, ctypes.c_ulong(0))
    xlib.XFlush(display)
    time.sleep(0.02)

def type_cmd(text, wait=0.5):
    print(f'  Typing: {text}')
    for ch in text:
        if ch in KEYSYM_MAP:
            kc = xlib.XKeysymToKeycode(display, ctypes.c_ulong(KEYSYM_MAP[ch]))
            press_key(kc, shift=(ch in SHIFT_CHARS))
    press_key(enter_code)
    time.sleep(wait)

# Find current CIW window ID dynamically
res = subprocess.run(["xwininfo", "-root", "-tree"], env={"DISPLAY": ":0", "HOME": "/home/lary"}, capture_output=True, text=True)
ciw_id = 0x2a00008
adel_id = 0x2a00470

print(f"Using CIW ID: {hex(ciw_id)}, ADE L ID: {hex(adel_id)}")

# 1. Focus and clear CIW input line
if ciw_id:
    xlib.XRaiseWindow(display, ctypes.c_ulong(ciw_id))
    xlib.XFlush(display)
    time.sleep(0.3)
    # Click command line input (bottom of CIW)
    click_at(1030 + 200, 734 + 325)
    time.sleep(0.2)
    # Clear line using Ctrl+U then Escape then Backspace
    press_key(u_code, ctrl=True)
    press_key(esc_code)
    for _ in range(30):
        press_key(bs_code)
    press_key(enter_code)
    time.sleep(0.3)

# 2. Write clean SKILL command to /tmp/run_adel.il
skill_content = """
sevNetlistAndRun('sevSession1)
"""
with open('/tmp/run_adel.il', 'w') as f:
    f.write(skill_content)

# 3. Execute via CIW: load("/tmp/run_adel.il")
type_cmd('load("/tmp/run_adel.il")', wait=2.0)

xlib.XCloseDisplay(display)
print("Trigger complete!")
