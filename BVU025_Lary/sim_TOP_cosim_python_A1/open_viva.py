#!/usr/bin/env python3
import ctypes, time, os, sys
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
XK_Return  = ctypes.c_ulong(0xFF0D)
XK_Shift_L = ctypes.c_ulong(0xFFE1)
enter_code = xlib.XKeysymToKeycode(display, XK_Return)
shift_code = xlib.XKeysymToKeycode(display, XK_Shift_L)

SHIFT_CHARS = set('"<>?:{}|~!@#$%^&*()_+ABCDEFGHIJKLMNOPQRSTUVWXYZ')
KEYSYM_MAP = {c: ord(c) for c in 'abcdefghijklmnopqrstuvwxyz0123456789 !"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'}
for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
    KEYSYM_MAP[c] = ord(c)

CIW_ID = 0x2e00008
CIW_X, CIW_Y = 1139 + 350, 792 + 290

def click_at(x, y):
    xtst.XTestFakeMotionEvent(display, -1, x, y, ctypes.c_ulong(0))
    xlib.XFlush(display)
    time.sleep(0.15)
    xtst.XTestFakeButtonEvent(display, 1, True, ctypes.c_ulong(0))
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
        xtst.XTestFakeKeyEvent(display, shift_code, True, ctypes.c_ulong(0))
        time.sleep(0.005)
    xtst.XTestFakeKeyEvent(display, kc, True, ctypes.c_ulong(0))
    time.sleep(0.012)
    xtst.XTestFakeKeyEvent(display, kc, False, ctypes.c_ulong(0))
    time.sleep(0.012)
    if need_shift:
        xtst.XTestFakeKeyEvent(display, shift_code, False, ctypes.c_ulong(0))
        time.sleep(0.005)

def type_cmd(text, wait=0.5):
    print(f'  CIW>>> {text}')
    for ch in text:
        type_char(ch)
    xlib.XFlush(display)
    time.sleep(0.2)
    xtst.XTestFakeKeyEvent(display, enter_code, True, ctypes.c_ulong(0))
    xlib.XFlush(display)
    time.sleep(0.05)
    xtst.XTestFakeKeyEvent(display, enter_code, False, ctypes.c_ulong(0))
    xlib.XFlush(display)
    time.sleep(wait)

xlib.XRaiseWindow(display, ctypes.c_ulong(CIW_ID))
xlib.XFlush(display)
time.sleep(0.6)
click_at(CIW_X, CIW_Y)
time.sleep(0.4)

IMG = "/home/lary/project/BVU025/SCH/cosim/pattern/TM14/images/cosim_waveform.png"
print("Opening waveform image via sh()...")
type_cmd(f'sh("/home/lary/bin/open_waveform.py \\"{IMG}\\"")', wait=2.0)

xlib.XCloseDisplay(display)
print("Done!")
