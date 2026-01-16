# NeverLiie IPC Protocol

This document outlines the **Inter-Process Communication (IPC)** system for the NeverLiie suite.

It is designed to create a **Mesh Network** where the Launcher, Terminal, and Status Bar can:
1.  **Talk to each other** with zero latency (using Windows Named Pipes).
2.  **Explicitly Wake each other:** Processes are independent, but can request another component to start via the Registry.
3.  **Self-Maintain:** Automatically prune registry entries if executables or scripts are moved/deleted (Zombie Pruning).
4.  **Enforce Singletons:** Ensure only one instance of a specific app runs at a time.
5.  **Work seamlessly** regardless of execution mode (Python Script vs Nuitka/PyInstaller Exe).
6.  **Handle Heavy Tasks:** Support threaded execution, streaming progress updates, and task cancellation.
7.  **Magic Proxy API:** Call remote functions as if they were local python objects.

## The Architecture

Instead of hardcoding paths, we use a **Dynamic Registry**.
1.  **Singleton Check:** On startup, the app checks if its named pipe is already active. If yes, it exits immediately.
2.  **Self-Registration:** If unique, it registers its launch command (Python script vs Compiled EXE) to `~/.neverliie/registry.json`.
3.  **Service Discovery:** When App A needs App B:
    *   It checks if App B is online (`ping`).
    *   If offline, it must explicitly `wake` App B.
    *   The IPC lib reads `registry.json` and spawns the process detached.

## Implementation

The system is modularized into the `ipclib` package. Copy the entire `ipclib/` folder into the root of your component.

## Usage Examples

### 1. The Provider (Server)
The API uses **Decorators** to expose functions. It feels like Flask or FastAPI.

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
The new API uses **Proxies** but requires **Explicit Lifecycle Management**. You must check if a peer is alive before calling it.

```python
# launcher/main.py
from ipclib import NeverLiieIPC, PeerOfflineError, RemoteExecutionError

ipc = NeverLiieIPC('launcher')

def update_ui():
    # 1. Get the proxy object (This is lazy, no connection yet)
    bar = ipc.get_peer('statusbar')
    
    # 2. Check Lifecycle
    if not ipc.ping('statusbar'):
        print("Status bar is sleeping. Waking...")
        try:
            # 'wake' reads the registry and launches the app.
            # It blocks until the app responds to pings or times out.
            ipc.wake('statusbar', timeout=5.0)
        except PeerOfflineError:
            print("Failed to wake statusbar (Application missing?).")
            return

    try:
        # 3. Call methods naturally
        stats = bar.get_stats(_timeout=2.0)
        print(f"Battery: {stats['battery']}%")
        
    except PeerOfflineError:
        print("Peer died during execution.")
    except RemoteExecutionError as e:
        print(f"RPC Logic Failed: {e}")
```

### 3. Streaming & Cancellation
For heavy operations, pass `_stream=True` to the proxy method.

**Client Side:**
```python
def run_scan():
    scanner = ipc.get_peer('statusbar')
    
    # Ensure it's running first
    if not ipc.ping('statusbar'):
        ipc.wake('statusbar')

    # 1. _stream=True tells the proxy to expect a generator
    stream = scanner.full_scan("C:/Logs", _stream=True)
    
    try:
        for filename in stream:
            print(f"Progress: {filename}")
            
            # 2. Cancellation:
            if user_pressed_cancel:
                stream.cancel() # Sends signal to server to kill the specific task
                break
                
    except PeerOfflineError:
        print("Scanner crashed!")
    except Exception as e:
        print(f"Stream error: {e}")
```

## API Reference

### `NeverLiieIPC(app_name)`
Initializes the IPC node.
*   **Singleton:** Exits process if `app_name` is already running.
*   **Registry:** Saves launch credentials to `~/.neverliie/registry.json`.

### Lifecycle Methods
*   `ipc.ping(target_name)`: Returns `bool`. Checks if target is currently running.
*   `ipc.wake(target_name, timeout=5.0)`: Returns `True` or raises `PeerOfflineError`. Explicitly launches the target from registry and waits for it to become responsive.

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
    *   `_stream`: (bool) If `True`, returns an `IPCStream` iterator.
*   **Exceptions:** Raises `PeerOfflineError` if the process is not running.

## How "Mixed Mode" Works (Under the Hood)

The `RegistryManager` automatically detects how the app is running so `ipc.wake()` works in both Dev and Prod:

1.  **Development (Python Script):**
    *   Detected via `sys.frozen == False`.
    *   Registry: `cmd: ["python.exe", "path/to/main.py"]`.
    
2.  **Production (Nuitka/PyInstaller):**
    *   Detected via `sys.frozen == True`.
    *   Registry: `cmd: ["path/to/compiled_app.exe"]`.