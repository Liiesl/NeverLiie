# NeverLiie IPC Protocol

This document outlines the **Inter-Process Communication (IPC)** system for the NeverLiie suite.

It is designed to create a **Mesh Network** where the Launcher, Terminal, and Status Bar can:
1.  **Talk to each other** with zero latency (using Windows Named Pipes).
2.  **Launch each other** if one component is missing/crashed.
3.  **Self-Heal:** Automatically prune registry entries if files are moved/deleted.
4.  **Enforce Singletons:** Ensure only one instance of a specific app runs at a time.
5.  **Work seamlessly** regardless of execution mode (Python Script vs Nuitka/PyInstaller Exe).
6.  **Handle Heavy Tasks:** Support threaded execution, streaming progress updates, and task cancellation.

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
import uuid
import types
from multiprocessing.connection import Listener, Client

# --- CONFIGURATION ---
REGISTRY_DIR = os.path.join(os.path.expanduser("~"), ".neverliie")
REGISTRY_FILE = os.path.join(REGISTRY_DIR, "registry.json")
PIPE_PREFIX = r'\\.\pipe\NeverLiie_'

class IPCStream:
    """Helper class to handle the iterator and cancellation on the client side."""
    def __init__(self, ipc_instance, target, task_id, conn):
        self._ipc = ipc_instance
        self._target = target
        self._task_id = task_id
        self._conn = conn
        self._active = True

    def __iter__(self):
        return self

    def __next__(self):
        if not self._active: raise StopIteration
        try:
            msg = self._conn.recv()
            if msg.get('status') == 'stream_end':
                self._active = False
                self._conn.close()
                raise StopIteration
            if msg.get('status') == 'error':
                self._active = False
                raise Exception(msg.get('msg'))
            return msg.get('data')
        except (EOFError, OSError):
            self._active = False
            raise StopIteration

    def cancel(self):
        """Sends a signal to the server to terminate this specific task."""
        if self._active:
            self._active = False
            try: self._conn.close() 
            except: pass
            # Send cancel command via a NEW connection to interrupt the server
            self._ipc.call(self._target, '__cancel_task__', task_id=self._task_id)

class NeverLiieIPC:
    def __init__(self, app_name):
        self.app_name = app_name
        self.pipe_address = f"{PIPE_PREFIX}{app_name}"
        self.methods = {}
        self.active_tasks = {} # Stores {task_id: stop_event}
        self.active_tasks_lock = threading.Lock()
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
                            # Accept connection and spawn thread immediately
                            conn = listener.accept()
                            t = threading.Thread(target=self._handle_client_connection, args=(conn,), daemon=True)
                            t.start()
                        except (EOFError, OSError): pass 
            except Exception: time.sleep(1)

    def _handle_client_connection(self, conn):
        task_id = None
        try:
            msg = conn.recv()
            method_name = msg.get('method')

            # 1. Internal: Cancel Request
            if method_name == '__cancel_task__':
                tid = msg.get('kwargs', {}).get('task_id')
                with self.active_tasks_lock:
                    if tid in self.active_tasks:
                        self.active_tasks[tid].set() # Signal thread to stop
                conn.send({'status': 'ok'})
                return

            # 2. Ping
            if method_name == '__ping__':
                conn.send(True)
                return

            # 3. User Function
            func = self.methods.get(method_name)
            if not func:
                conn.send({'status': 'error', 'msg': 'Method not found'})
                return

            # Execute
            res = func(*msg.get('args', []), **msg.get('kwargs', {}))

            # CHECK: Is this a Generator?
            if isinstance(res, types.GeneratorType):
                task_id = str(uuid.uuid4())
                stop_event = threading.Event()
                with self.active_tasks_lock: self.active_tasks[task_id] = stop_event

                conn.send({'status': 'stream_start', 'task_id': task_id})

                try:
                    for item in res:
                        if stop_event.is_set(): break 
                        conn.send({'status': 'progress', 'data': item})
                    conn.send({'status': 'stream_end'})
                finally:
                    with self.active_tasks_lock:
                        if task_id in self.active_tasks: del self.active_tasks[task_id]
            else:
                # Standard Return
                conn.send({'status': 'ok', 'data': res})

        except (BrokenPipeError, EOFError): pass 
        except Exception as e:
            try: conn.send({'status': 'error', 'msg': str(e)})
            except: pass
        finally:
            try: conn.close()
            except: pass

    # --- CLIENT SIDE (Calling) ---
    def call(self, target, method, *args, **kwargs):
        """
        Standard synchronous call.
        Attempts to call a method on 'target'. 
        If 'target' is offline, it reads registry and launches it.
        """
        return self._connect_and_send(target, method, args, kwargs, stream=False)

    def stream(self, target, method, *args, **kwargs):
        """Returns an iterable IPCStream object for long-running tasks."""
        return self._connect_and_send(target, method, args, kwargs, stream=True)

    def _connect_and_send(self, target, method, args, kwargs, stream):
        target_pipe = f"{PIPE_PREFIX}{target}"
        
        def try_connect():
            try:
                conn = Client(target_pipe)
                conn.send({'method': method, 'args': args, 'kwargs': kwargs})
                return conn
            except (FileNotFoundError, ConnectionRefusedError): return None

        conn = try_connect()
        
        if not conn:
            print(f"[IPC] {target} offline. Checking registry...")
            if self._launch_from_registry(target):
                time.sleep(1.5)
                conn = try_connect()
        
        if not conn: return None if not stream else []

        if stream:
            header = conn.recv()
            if header.get('status') == 'stream_start':
                return IPCStream(self, target, header['task_id'], conn)
            else:
                conn.close()
                return [] 
        else:
            try:
                if conn.poll(timeout=kwargs.get('_timeout', 5.0)):
                    res = conn.recv()
                    conn.close()
                    return res
                else:
                    conn.close()
                    return {'status': 'error', 'msg': 'Timeout'}
            except: return {'status': 'error', 'msg': 'Connection Error'}

    def _launch_from_registry(self, target):
        if not os.path.exists(REGISTRY_FILE): return False
        
        try:
            with open(REGISTRY_FILE, 'r') as f:
                data = json.load(f)
            
            info = data.get(target)
            if not info: return False


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
This script needs data from the Provider. It doesn't care if the Provider is running or not. It supports timeouts.

```python
# launcher/main.py
from neverliie_ipc import NeverLiieIPC

ipc = NeverLiieIPC('launcher')

def show_dashboard():
    # 1. Ask for stats.
    # 2. If Status Bar is closed, IPC will auto-launch it based on JSON info.
    # 3. If registry info is stale (file deleted), IPC cleans it up and returns None.
    # 4. We can pass _timeout=X.X to wait longer for heavy tasks (default 5s).
    response = ipc.call('statusbar', 'get_stats', _timeout=3.0)
    
    if response and response['status'] == 'ok':
        data = response['data']
        print(f"Battery: {data['battery']}%")
    else:
        print("Failed to contact status bar.")
```

### 3. Streaming & Cancellation (Long Running Tasks)
For heavy operations (e.g., file scanning), use Python generators (`yield`). The IPC wrapper handles the streaming automatically.

**Server Side:**
```python
def deep_scan(folder):
    files = get_all_files(folder)
    for f in files:
        # yield progress updates instead of returning once
        yield {"status": "scanning", "file": f}
        time.sleep(0.1)

ipc.expose('deep_scan', deep_scan)
```

**Client Side:**
```python
# Use ipc.stream instead of ipc.call
stream = ipc.stream('scanner_app', 'deep_scan', folder="C:/Logs")

for msg in stream:
    print(f"Scanning: {msg['file']}")
    
    # If the user clicks "Cancel" in the UI:
    if user_clicked_stop:
        stream.cancel() # Stops the loop on the server immediately
        break
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
