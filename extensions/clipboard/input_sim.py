import ctypes
import time
from ctypes import wintypes

# Win32 Constants
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
VK_CONTROL = 0x11
VK_V = 0x56

# C Types for SendInput
class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_ulong)
    ]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("ki", KEYBDINPUT)
    ]

def send_ctrl_v():
    """Simulates pressing Ctrl+V to paste content."""
    user32 = ctypes.windll.user32
    
    # Helper to create INPUT structure
    def create_input(vk, flags):
        x = INPUT()
        x.type = INPUT_KEYBOARD
        x.ki.wVk = vk
        x.ki.dwFlags = flags
        return x

    # 1. Press Ctrl
    inp_ctrl_down = create_input(VK_CONTROL, 0)
    # 2. Press V
    inp_v_down = create_input(VK_V, 0)
    # 3. Release V
    inp_v_up = create_input(VK_V, KEYEVENTF_KEYUP)
    # 4. Release Ctrl
    inp_ctrl_up = create_input(VK_CONTROL, KEYEVENTF_KEYUP)

    inputs = (INPUT * 4)(inp_ctrl_down, inp_v_down, inp_v_up, inp_ctrl_up)
    
    # SendInput returns the number of events inserted
    user32.SendInput(4, inputs, ctypes.sizeof(INPUT))