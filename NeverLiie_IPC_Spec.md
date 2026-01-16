# NeverLiie IPC Protocol

This document outlines the **Inter-Process Communication (IPC)** system for the NeverLiie suite.

It is designed to create a **Mesh Network** where the Launcher, Terminal, and Status Bar can:
1.  **Talk to each other** with zero latency (using Windows Named Pipes).
2.  **Launch each other** if one component is missing/crashed.
3.  **Self-Heal:** Automatically prune registry entries if files are moved/deleted.
4.  **Enforce Singletons:** Ensure only one instance of a specific app runs at a time.
5.  **Work seamlessly** regardless of execution mode (Python Script vs Nuitka/PyInstaller Exe).

## The Architecture

Instead of hardcoding paths, we use a **Dynamic Registry**.
1.  **Singleton Check:** On startup, the app checks if its named pipe is already active. If yes, it exits immediately (preventing duplicates).
2.  **Self-Registration:** If unique, it registers its absolute path to `~/.neverliie/registry.json`.
3.  **Service Discovery:** When App A needs App B:
    *   Tries the Named Pipe.
    *   If failed, reads `registry.json`.
    *   **Pruning:** If the path in the registry does not exist, it deletes the entry.
    *   If valid, it executes the command to spawn App B.

## Implementation (`neverliie_ipc.py`)

Copy this file into the root of **every** component directory (`launcher/`, `terminal/`, `statusbar/`). It requires no external dependencies (`pip` install not required).

```python
import sys
import os
import json
import time
import subprocess
import threading
from multiprocessing.connection import Listener, Client

# --- CONFIGURATION ---
# The central brain of the operation.
REGISTRY_DIR = os.path.join(os.path.expanduser("~"), ".neverliie")
REGISTRY_FILE = os.path.join(REGISTRY_DIR, "registry.json")
PIPE_PREFIX = r'\\.\pipe\NeverLiie_'

class NeverLiieIPC:
    def __init__(self, app_name):
        self.app_name = app_name
        self.pipe_address = f"{PIPE_PREFIX}{app_name}"
        self.methods = {}
        self.running = True

        # --- SINGLETON ENFORCEMENT ---
        # Before starting, check if this app is already running.
        # If we can connect to our own pipe, someone is already home.
        try:
            with Client(self.pipe_address) as conn:
                print(f"[IPC] {app_name} is already running. Exiting.")
                sys.exit(0)
        except (OSError, ConnectionRefusedError):
            pass # No instance found, proceed to start.

        # Ensure registry directory exists
        if not os.path.exists(REGISTRY_DIR):
            try: os.makedirs(REGISTRY_DIR)
            except FileExistsError: pass

        # 1. Register this app's location so others can find it
        self._update_registry()

        # 2. Start the Listener Thread
        self._thread = threading.Thread(target=self._server_loop, daemon=True)
        self._thread.start()

    # --- REGISTRY LOGIC ---
    def _update_registry(self):
        """
        Determines if we are a Script or Exe and saves the command to JSON.
        Includes retry logic to handle file locking contention.
        """
        entry = self._get_launch_info()
        
        # Retry up to 5 times if file is locked by another app
        for _ in range(5):
            try:
                data = {}
                if os.path.exists(REGISTRY_FILE):
                    with open(REGISTRY_FILE, 'r') as f:
                        try: data = json.load(f)
                        except json.JSONDecodeError: pass 

                data[self.app_name] = entry

                with open(REGISTRY_FILE, 'w') as f:
                    json.dump(data, f, indent=4)
                return 
            except PermissionError:
                time.sleep(0.05)
            except Exception as e:
                print(f"[IPC] Registry Write Error: {e}")
                return

    def _get_launch_info(self):
        """Detects execution mode (Nuitka/PyInstaller vs Raw Python)."""
        # sys.frozen is set by Nuitka/PyInstaller
        if getattr(sys, 'frozen', False):
            return {
                'type': 'binary',
                'cmd': [sys.executable], 
                'cwd': os.path.dirname(sys.executable)
            }
        else:
            return {
                'type': 'script',
                'cmd': [sys.executable, os.path.abspath(sys.argv[0])], 
                'cwd': os.getcwd()
            }

    # --- SERVER SIDE (Listening) ---
    def expose(self, name, func):
        """Register a function to be callable by other apps."""
        self.methods[name] = func

    def _server_loop(self):
        while self.running:
            try:
                # Windows Named Pipe Listener
                with Listener(self.pipe_address) as listener:
                    while self.running:
                        try:
                            with listener.accept() as conn:
                                msg = conn.recv()
                                
                                # 1. Health Check
                                if msg.get('method') == '__ping__':
                                    conn.send(True)
                                    continue

                                # 2. Function Call
                                method_name = msg.get('method')
                                func = self.methods.get(method_name)
                                
                                if func:
                                    try:
                                        # Execute local function
                                        res = func(*msg.get('args', []), **msg.get('kwargs', {}))
                                        conn.send({'status': 'ok', 'data': res})
                                    except Exception as e:
                                        conn.send({'status': 'error', 'msg': str(e)})
                                else:
                                    conn.send({'status': 'error', 'msg': 'Method not found'})
                        except EOFError:
                            pass 
                        except Exception:
                            pass 
            except Exception:
                # Pipe error (collision/restart), wait brief moment
                time.sleep(1)

    # --- CLIENT SIDE (Calling) ---
    def call(self, target, method, *args, **kwargs):
        """
        Attempts to call a method on 'target'. 
        If 'target' is offline, it reads registry and launches it.
        """
        target_pipe = f"{PIPE_PREFIX}{target}"

        # Attempt 1: Direct Connection
        res = self._send_request(target_pipe, method, args, kwargs)
        if res is not None: return res

        # Attempt 2: Launch and Retry
        print(f"[IPC] {target} offline. Checking registry...")
        if self._launch_from_registry(target):
            # Give the process 1.0s to start up and bind the pipe
            time.sleep(1.0)
            return self._send_request(target_pipe, method, args, kwargs)
        
        return None

    def _send_request(self, pipe, method, args, kwargs):
        try:
            with Client(pipe) as conn:
                conn.send({'method': method, 'args': args, 'kwargs': kwargs})
                if conn.poll(timeout=3.0): # 3s Timeout prevents hanging
                    return conn.recv()
        except (FileNotFoundError, ConnectionRefusedError):
            return None # Offline
        except Exception:
            return None

    def _launch_from_registry(self, target):
        if not os.path.exists(REGISTRY_FILE): return False
        
        try:
            with open(REGISTRY_FILE, 'r') as f:
                data = json.load(f)
            
            info = data.get(target)
            if not info: return False

            cmd = info['cmd']
            cwd = info['cwd']

            # Validate executable exists before trying to run
            # 'cmd' is either ['path/to/exe'] or ['python', 'path/to/script']
            exe_path = cmd[0] if len(cmd) == 1 else cmd[1]
            
            # --- ZOMBIE REGISTRY PRUNING ---
            if not os.path.exists(exe_path):
                print(f"[IPC] Target not found at {exe_path}. Pruning registry.")
                del data[target]
                try:
                    with open(REGISTRY_FILE, 'w') as f:
                        json.dump(data, f, indent=4)
                except: pass
                return False
            # -------------------------------

            # Launch DETACHED so it survives if this process dies
            subprocess.Popen(
                cmd, 
                cwd=cwd,
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                close_fds=True,
                shell=False
            )
            return True
        except Exception as e:
            print(f"[IPC] Launch failed: {e}")
            return False
```

## Usage Examples

### 1. The Provider (e.g., Status Bar)
This script holds the data or controls. It needs to expose functions.

```python
# statusbar/main.py
from neverliie_ipc import NeverLiieIPC
import psutil

# Initialize (This automatically registers the app, or exits if already running)
ipc = NeverLiieIPC('statusbar')

# Define Logic
def get_stats():
    return {
        "battery": psutil.sensors_battery().percent,
        "cpu": psutil.cpu_percent()
    }

# Expose Logic
ipc.expose('get_stats', get_stats)

print("Status Bar running...")
# ... Start GUI Loop ...
```

### 2. The Consumer (e.g., Launcher)
This script needs data from the Provider. It doesn't care if the Provider is running or not.

```python
# launcher/main.py
from neverliie_ipc import NeverLiieIPC

ipc = NeverLiieIPC('launcher')

def show_dashboard():
    # 1. Ask for stats.
    # 2. If Status Bar is closed, IPC will auto-launch it based on JSON info.
    # 3. If registry info is stale (file deleted), IPC cleans it up and returns None.
    response = ipc.call('statusbar', 'get_stats')
    
    if response and response['status'] == 'ok':
        data = response['data']
        print(f"Battery: {data['battery']}%")
    else:
        print("Failed to contact status bar.")
```

### 3. The Controller (e.g., Terminal Client)
This script commands the Server.

```python
# terminal/client.py
import os
from neverliie_ipc import NeverLiieIPC

# We don't expose anything, we just send commands.
ipc = NeverLiieIPC('terminal_client')

cwd = os.getcwd()

# If 'terminal_server' is crashed, this restarts it.
ipc.call('terminal_server', 'new_tab', cwd=cwd)
```

## How "Mixed Mode" Works

1.  **Development:**
    *   You run `python statusbar/main.py`.
    *   Registry updates: `cmd: ["python.exe", "path/to/main.py"]`.
    *   Launcher (running as exe) reads this and runs python to start the bar.
2.  **Production:**
    *   You compile `nuitka statusbar/main.py -o statusbar.exe`.
    *   You run `statusbar.exe` **once**.
    *   Registry updates: `cmd: ["path/to/statusbar.exe"]`.
    *   Launcher reads this and runs the `.exe` directly.
