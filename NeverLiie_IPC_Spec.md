# NeverLiie IPC Protocol

This document outlines the **Inter-Process Communication (IPC)** system for the NeverLiie suite.

It is designed to create a **Mesh Network** where the Launcher, Terminal, and Status Bar can:
1.  **Talk to each other** with zero latency (using Windows Named Pipes).
2.  **Launch each other** automatically if a target component is missing or crashed.
3.  **Self-Heal:** Automatically prune registry entries if executables or scripts are moved/deleted (Zombie Pruning).
4.  **Enforce Singletons:** Ensure only one instance of a specific app runs at a time.
5.  **Work seamlessly** regardless of execution mode (Python Script vs Nuitka/PyInstaller Exe).
6.  **Handle Heavy Tasks:** Support threaded execution, streaming progress updates, and task cancellation.
7.  **Magic Proxy API:** Call remote functions as if they were local python objects.

## The Architecture

Instead of hardcoding paths, we use a **Dynamic Registry**.
1.  **Singleton Check:** On startup, the app checks if its named pipe is already active. If yes, it exits immediately.
2.  **Self-Registration:** If unique, it registers its launch command (Python script vs Compiled EXE) to `~/.neverliie/registry.json`.
3.  **Service Discovery:** When App A needs App B:
    *   It attempts to connect to the Named Pipe.
    *   If failed, it reads `registry.json`.
    *   It validates the path exists (cleaning up the registry if the file is gone).
    *   It spawns the process detached from the parent.

## Implementation

The system is modularized into the `ipclib` package. Copy the entire `ipclib/` folder into the root of your component.

## Usage Examples

### 1. The Provider (Server)
The new API uses **Decorators** to expose functions. It feels like Flask or FastAPI.

```python
# statusbar/main.py
import time
import psutil
from ipclib import NeverLiieIPC

# 1. Initialize (Auto-registers app, enforces singleton)
ipc = NeverLiieIPC('statusbar')

# 2. Expose functions using the decorator
@ipc.expose
def get_stats():
    return {
        "battery": psutil.sensors_battery().percent,
        "cpu": psutil.cpu_percent()
    }

# 3. You can also alias functions
@ipc.expose("full_scan")
def long_running_task(folder):
    files = get_files(folder)
    for f in files:
        time.sleep(0.1)
        yield f"Scanned {f}" # Yielding creates a stream!

print("Status Bar running...")
# ... Start GUI Loop ...
```

### 2. The Consumer (Client)
The new API uses **Proxies**. You don't need to manually call `ipc.call`. You simply ask for a peer and call methods on it.

```python
# launcher/main.py
from ipclib import NeverLiieIPC, RemoteExecutionError

ipc = NeverLiieIPC('launcher')

def update_ui():
    # 1. Get the proxy object
    bar = ipc.get_peer('statusbar')
    
    try:
        # 2. Call methods naturally
        # (This auto-launches 'statusbar' if it isn't running)
        stats = bar.get_stats(_timeout=2.0)
        print(f"Battery: {stats['battery']}%")
        
    except RemoteExecutionError as e:
        print(f"RPC Failed: {e}")
```

### 3. Streaming & Cancellation
For heavy operations, simply pass `_stream=True` to the proxy method. This returns an iterator.

**Client Side:**
```python
def run_scan():
    scanner = ipc.get_peer('statusbar')
    
    # 1. _stream=True tells the proxy to expect a generator
    stream = scanner.full_scan("C:/Logs", _stream=True)
    
    try:
        for filename in stream:
            print(f"Progress: {filename}")
            
            # 2. Cancellation:
            if user_pressed_cancel:
                stream.cancel() # Sends signal to server to kill the specific task
                break
                
    except Exception as e:
        print(f"Stream error: {e}")
```

## API Reference

### `NeverLiieIPC(app_name)`
Initializes the IPC node.
*   **Singleton:** Exits process if `app_name` is already running.
*   **Registry:** Saves launch credentials to `~/.neverliie/registry.json`.

### `ipc.expose`
Decorator. Registers a function to be callable remotely.
*   `@ipc.expose`: Uses the function's actual name.
*   `@ipc.expose("alias")`: Uses a custom name.

### `ipc.get_peer(target_name)`
Returns a `RemotePeer` proxy object.

### `RemotePeer` Methods
*   `method_name(*args, **kwargs)`: Calls the remote method.
*   **Magic Kwargs:**
    *   `_timeout`: (float) Seconds to wait for a response (Default: 5.0).
    *   `_stream`: (bool) If `True`, returns an `IPCStream` iterator instead of a direct result.

## How "Mixed Mode" Works (Under the Hood)

The `RegistryManager` automatically detects how the app is running:

1.  **Development (Python Script):**
    *   Detected via `sys.frozen == False`.
    *   Registry: `cmd: ["python.exe", "path/to/main.py"]`.
    
2.  **Production (Nuitka/PyInstaller):**
    *   Detected via `sys.frozen == True`.
    *   Registry: `cmd: ["path/to/compiled_app.exe"]`.

When `get_peer('target')` is called, if the target is offline, the IPC library executes the command found in the registry.
