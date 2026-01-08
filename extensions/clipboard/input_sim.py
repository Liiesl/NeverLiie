# extensions/clipboard/input_sim.py
import ctypes
from ctypes import wintypes

# Win32 Constants
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
VK_LCONTROL = 0xA2 # Left Control
VK_V = 0x56

# Architecture check
is_64bit = ctypes.sizeof(ctypes.c_void_p) == 8
ULONG_PTR = ctypes.c_ulonglong if is_64bit else ctypes.c_ulong

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR)
    ]

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR)
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD)
    ]

# The Union is critical for correct size calculation
class INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT)
    ]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("u", INPUT_UNION)
    ]

def send_ctrl_v():
    user32 = ctypes.windll.user32
    
    def create_input(vk, flags):
        x = INPUT()
        x.type = INPUT_KEYBOARD
        x.u.ki.wVk = vk
        x.u.ki.dwFlags = flags
        return x

    inputs = (INPUT * 4)(
        create_input(VK_LCONTROL, 0),
        create_input(VK_V, 0),
        create_input(VK_V, KEYEVENTF_KEYUP),
        create_input(VK_LCONTROL, KEYEVENTF_KEYUP)
    )
    
    # On x64, sizeof(INPUT) should be 40. On x86, 28.
    # The previous code was sending 20, causing the failure.
    user32.SendInput(4, inputs, ctypes.sizeof(INPUT))