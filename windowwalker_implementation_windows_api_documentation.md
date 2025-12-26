# Window Walker — Windows API reference & how the plugin uses them

This document lists the Windows (Win32 / DWM) APIs called by the Microsoft.Plugin.WindowWalker plugin in PowerToys, describes each API (signature, parameters, behavior), and explains how the plugin uses it (file and high-level code flow). Use this as developer-facing reference for understanding the native interop in Window Walker.

Table of contents
- Overview / common patterns
- EnumWindows / EnumChildWindows
- GetWindowTextLength / GetWindowText
- GetClassName
- IsWindow / IsWindowVisible
- GetWindow / GetProp
- GetWindowLong (EX styles)
- GetWindowPlacement / ShowWindow / SetForegroundWindow
- SendMessage / SendMessageTimeout
- FlashWindow
- GetWindowThreadProcessId
- GetShellWindow
- DWM APIs: DwmGetWindowAttribute / DwmSetWindowAttribute / (DwmpActivateLivePreview)
- OpenProcess / GetProcessImageFileName / CloseHandle / error handling
- Win32Helpers.GetLastError usage / access denial check
- Patterns & examples (GCHandle + EnumWindows cancellation token, child-window search for UWP)
- How select/close/kill workflows map to the APIs
- Security/notes

---

Overview / common patterns
- The plugin uses a NativeMethods wrapper (PInvoke) to call user32.dll, kernel32.dll, dwmapi.dll and related APIs.
- Patterns in the plugin:
  - Enumerate top-level windows via EnumWindows, collect recent window handles, build Window objects.
  - Use GetWindowTextLength/GetWindowText and GetClassName to read title/class.
  - Query window and process properties via GetWindowThreadProcessId, OpenProcess + GetProcessImageFileName.
  - Use DWM attributes (DwmGetWindowAttribute) to detect cloak state and to control live preview via DwmSetWindowAttribute / DwmpActivateLivePreview.
  - Use GetWindowLong to check extended window styles (toolwindow / appwindow).
  - Use ShowWindow/SetForegroundWindow/SendMessage to switch to window or restore it; SendMessageTimeout/SC_CLOSE to close windows.
  - Use OpenProcess(AllAccess) to test if full access is denied (ERROR_ACCESS_DENIED) before offering “Kill process” action.
  - Use EnumChildWindows to find UWP child windows hosted by ApplicationFrameHost.exe to correct process attribution.

Where to look in code:
- Enumeration & collection: OpenWindows.cs, Window.cs (constructor, CreateWindowProcessInstance)
- Title/class/visibility: Window.cs
- DWM & live preview: LivePreview.cs, Window.cs (GetWindowCloakState)
- Process operations: WindowProcess.cs
- User interactions (close/kill): ContextMenuHelper.cs, ResultHelper.cs, Main.cs

---

EnumWindows / EnumChildWindows
Purpose
- Enumerate top-level windows (EnumWindows) and child windows of a window (EnumChildWindows).

Typical PInvoke
- [DllImport("user32.dll")]
  static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
- delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
- [DllImport("user32.dll")]
  static extern bool EnumChildWindows(IntPtr hWndParent, EnumWindowsProc lpEnumFunc, IntPtr lParam);

How plugin uses it
- OpenWindows.UpdateOpenWindowsList calls NativeMethods.EnumWindows with a callback that creates Window instances for each handle.
  - It passes a CancellationToken to EnumWindows via GCHandle/IntPtr (tokenHandleParam) so the callback can stop enumeration early if canceled.
  - The callback uses WindowEnumerationCallBack in OpenWindows.cs to filter windows (visible, not ownered, not tool window unless app window, cloaked status, desktop visibility).
- Window.CreateWindowProcessInstance uses EnumChildWindows in a background Task to search child windows (class starting with "Windows.UI.Core.") to find the real process of UWP windows that are hosted by ApplicationFrameHost.exe.

Notes
- The callback runs on the same thread where EnumWindows was called (user32 thread). The plugin uses GCHandle to pass managed CancellationToken safely.

---

GetWindowTextLength / GetWindowText
Purpose
- Get length of window title and retrieve the title text.

Typical PInvoke
- [DllImport("user32.dll", CharSet = CharSet.Auto, SetLastError = true)]
  static extern int GetWindowTextLength(IntPtr hWnd);
- [DllImport("user32.dll", CharSet = CharSet.Auto, SetLastError = true)]
  static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);

How plugin uses it
- Window.Title property (Window.cs) calls GetWindowTextLength() then GetWindowText() to build the displayed Title string for search and UI.
- If GetWindowText returns 0, Title returns empty string.

Notes
- The plugin uses this to display and fuzzy-match window titles.

---

GetClassName
Purpose
- Get the registered window class name of a window.

Typical PInvoke
- [DllImport("user32.dll", CharSet = CharSet.Auto, SetLastError = true)]
  static extern int GetClassName(IntPtr hWnd, StringBuilder lpClassName, int nMaxCount);

How plugin uses it
- Window.GetWindowClassName called in Window.ClassName to read the window class; used to filter out windows in enumeration (e.g., skip "Windows.UI.Core.CoreWindow" or use to find child window classes starting with "Windows.UI.Core." in CreateWindowProcessInstance).

---

IsWindow / IsWindowVisible
Purpose
- IsWindow: determine whether a handle is a valid window.
- IsWindowVisible: determine if a window is visible.

Typical PInvoke
- [DllImport("user32.dll")]
  static extern bool IsWindow(IntPtr hWnd);
- [DllImport("user32.dll")]
  static extern bool IsWindowVisible(IntPtr hWnd);

How plugin uses it
- Window.IsWindow property returns NativeMethods.IsWindow(Hwnd); used to validate handle existence before operations (close / kill checks).
- Window.Visible uses IsWindowVisible to decide if a window should be listed.

---

GetWindow / GetProp
Purpose
- GetWindow with GW_OWNER to see if window has owner (owner != IntPtr.Zero => not top-level).
- GetProp to read named property "ITaskList_Deleted".

Typical PInvoke
- [DllImport("user32.dll")]
  static extern IntPtr GetWindow(IntPtr hWnd, GetWindowCmd uCmd);
- [DllImport("user32.dll", CharSet = CharSet.Auto)]
  static extern IntPtr GetProp(IntPtr hWnd, string lpString);

How plugin uses it
- Window.IsOwner uses GetWindow(hWnd, GW_OWNER) == IntPtr.Zero to only include windows that have no owner (top-level).
- Window.TaskListDeleted uses GetProp(Hwnd, "ITaskList_Deleted") to detect windows removed from TaskList and exclude them.

---

GetWindowLong (extended window styles)
Purpose
- Retrieve window long values like extended styles (WS_EX_TOOLWINDOW, WS_EX_APPWINDOW).

Typical PInvoke
- [DllImport("user32.dll", SetLastError = true)]
  static extern IntPtr GetWindowLongPtr(IntPtr hWnd, int nIndex);
  (older: GetWindowLong for 32-bit)
- Constants: GWL_EXSTYLE, WS_EX_TOOLWINDOW, WS_EX_APPWINDOW.

How plugin uses it
- Window.IsToolWindow and Window.IsAppWindow test the EX style bits to decide whether to include windows (tool windows vs app windows) in listing.

---

GetWindowPlacement / ShowWindow / SetForegroundWindow
Purpose
- GetWindowPlacement: get show command (minimized/normal/maximized).
- ShowWindow: restore/minimize/maximize windows.
- SetForegroundWindow: bring window to foreground.

Typical PInvoke
- [DllImport("user32.dll")]
  static extern bool GetWindowPlacement(IntPtr hWnd, out WINDOWPLACEMENT lpwndpl);
- [DllImport("user32.dll")]
  static extern bool ShowWindow(IntPtr hWnd, ShowWindowCommand nCmdShow);
- [DllImport("user32.dll")]
  static extern bool SetForegroundWindow(IntPtr hWnd);

How plugin uses it
- Window.GetWindowSizeState uses GetWindowPlacement.ShowCmd to determine Minimized/Normal/Maximized for display and to choose restore behavior.
- Window.SwitchToWindow attempts SetForegroundWindow first for non-minimized or specific processes (IEXPLORE.EXE), otherwise shows/restore:
  - If minimized: call ShowWindow(... Restore).
  - If ShowWindow fails (e.g., plugin is not elevated while target is elevated), fallback uses SendMessage to SC_RESTORE.

Notes
- The plugin chooses between SetForegroundWindow and ShowWindow to avoid flashing issues or when SetForegroundWindow fails on minimized windows.
- ShowWindow can fail when process is elevated; plugin has fallback.

---

SendMessage / SendMessageTimeout / WM_SYSCOMMAND / SC_CLOSE / SC_RESTORE
Purpose
- Send messages to windows (close, restore) and use SendMessageTimeout when waiting with timeout.

Typical PInvoke
- [DllImport("user32.dll")]
  static extern IntPtr SendMessage(IntPtr hWnd, uint Msg, IntPtr wParam, IntPtr lParam);
- [DllImport("user32.dll")]
  static extern IntPtr SendMessageTimeout(IntPtr hWnd, uint Msg, IntPtr wParam, IntPtr lParam, uint fuFlags, uint uTimeout, out IntPtr lpdwResult);

How plugin uses it
- CloseThisWindowHelper uses SendMessageTimeout with WM_SYSCOMMAND / SC_CLOSE to signal the window to close with a 5000ms timeout.
- SwitchToWindow fallback uses SendMessage(hwnd, WM_SYSCOMMAND, SC_RESTORE, 0) to restore when ShowWindow doesn't work.

---

FlashWindow
Purpose
- Flash a window (for user attention) after switching to it.

Typical PInvoke
- [DllImport("user32.dll")]
  static extern bool FlashWindow(IntPtr hWnd, bool bInvert);

How plugin uses it
- Window.SwitchToWindow calls NativeMethods.FlashWindow(Hwnd, true) after bring-to-front / restore.

---

GetWindowThreadProcessId
Purpose
- Get process ID and thread ID for a window.

Typical PInvoke
- [DllImport("user32.dll")]
  static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);

How plugin uses it
- WindowProcess.GetProcessIDFromWindowHandle and GetThreadIDFromWindowHandle call GetWindowThreadProcessId to obtain process/thread ids used to build WindowProcess entries and for Process lookups.

---

GetShellWindow
Purpose
- Get the window handle for the shell (Explorer). Useful to decide whether a process is the shell.

Typical PInvoke
- [DllImport("user32.dll")]
  static extern IntPtr GetShellWindow();

How plugin uses it
- WindowProcess.IsShellProcess returns whether GetProcessIDFromWindowHandle(GetShellWindow()) equals ProcessID. Used to hide the "Kill" option for Explorer host process.

---

DWM APIs: DwmGetWindowAttribute / DwmSetWindowAttribute / DwmpActivateLivePreview
Purpose
- DwmGetWindowAttribute: query attributes such as Cloaked for a window (detect cloaked windows).
- DwmSetWindowAttribute: set composition/feature attributes for a window (used here to exclude a window from live preview).
- DwmpActivateLivePreview: used by plugin to activate/deactivate Windows *Live Preview* behavior (the plugin calls NativeMethods.DwmpActivateLivePreview). Note: DwmpActivateLivePreview is not a commonly-documented public API — it’s a DWM/desktop composition function exposed on some versions of Windows.

Typical PInvoke
- [DllImport("dwmapi.dll")]
  static extern int DwmGetWindowAttribute(IntPtr hWnd, int dwAttribute, out int pvAttribute, int cbAttribute);
- [DllImport("dwmapi.dll")]
  static extern int DwmSetWindowAttribute(IntPtr hWnd, int dwAttribute, ref uint pvAttribute, int cbAttribute);
- [DllImport("dwmcore.dll" or "dwmapi.dll"?) — plugin calls DwmpActivateLivePreview via NativeMethods]
  static extern int DwmpActivateLivePreview(bool enable, IntPtr targetWindow, IntPtr windowToSpare, LivePreviewTrigger trigger, IntPtr unknown);

How plugin uses it
- Window.GetWindowCloakState uses DwmGetWindowAttribute(Hwnd, (int)DwmWindowAttributes.Cloaked, out int isCloakedState, sizeof(uint)) to determine if a window is cloaked by DWM (App, Shell, Inherited). This is used to filter out preloaded UWP windows and other cloaked windows (OpenWindows.WindowEnumerationCallBack and Window.IsCloaked).
- LivePreview.SetWindowExclusionFromLivePreview calls DwmSetWindowAttribute with DwmNCRenderingPolicies.Enabled to exclude a window from live preview rendering.
- LivePreview.ActivateLivePreview and DeactivateLivePreview call NativeMethods.DwmpActivateLivePreview to enable a live-preview mode (plugin uses DwmpActivateLivePreview to temporarily make other windows transparent and show a selected window). The plugin passes LivePreviewTrigger.Superbar or LivePreviewTrigger.AltTab depending on scenario.

Notes & caution
- DWM attributes are version-specific. Cloak attributes are supported starting with some Windows 8/10 APIs. DwmpActivateLivePreview may be an internal/undocumented function; behavior could change between OS versions. The plugin code assumes success and ignores return values.

---

OpenProcess / GetProcessImageFileName / CloseHandle
Purpose
- OpenProcess: obtain a handle to a process to query details or test access.
- GetProcessImageFileName: read the process image filename (path).
- CloseHandle: close the handle.

Typical PInvoke
- [DllImport("kernel32.dll", SetLastError = true)]
  static extern IntPtr OpenProcess(ProcessAccessFlags processAccess, bool bInheritHandle, int processId);
- [DllImport("psapi.dll", CharSet = CharSet.Auto)]
  static extern int GetProcessImageFileName(IntPtr hProcess, StringBuilder lpImageFileName, int nSize);
- [DllImport("kernel32.dll", SetLastError = true)]
  static extern bool CloseHandle(IntPtr hObject);

How plugin uses it
- WindowProcess.GetProcessNameFromProcessID opens the process with ProcessAccessFlags.QueryLimitedInformation and calls GetProcessImageFileName to obtain the full path to the process executable; it then extracts the filename (last component after backslash) and returns it.
- WindowProcess.TestProcessAccessUsingAllAccessFlag opens the process with ProcessAccessFlags.AllAccess and checks Win32Helpers.GetLastError() for ERROR_ACCESS_DENIED (5). If denied, the plugin sets IsFullAccessDenied=true so the plugin will:
  - Hide the Kill menu for elevated processes if user set HideKillProcessOnElevatedProcesses.
  - When killing, if IsFullAccessDenied==true the plugin uses taskkill.exe with elevation (Helper.OpenInShell with RunAs) instead of Process.Kill.

Notes
- OpenProcess with different flags sets permission levels. The plugin closes handles via Win32Helpers.CloseHandleIfNotNull.

---

Win32Helpers.GetLastError usage / access denial check
Purpose
- After OpenProcess(AllAccess) the plugin uses Win32Helpers.GetLastError() to detect ERROR_ACCESS_DENIED (5).

How plugin uses it
- In WindowProcess.TestProcessAccessUsingAllAccessFlag, if GetLastError() == 5 (ERROR_ACCESS_DENIED), plugin sets IsFullAccessDenied = true. This controls UI (hide kill) and kill behavior (use elevated taskkill).

---

Patterns & examples

1) EnumWindows with cancellation token (OpenWindows.UpdateOpenWindowsList)
- The plugin wraps a CancellationToken in a GCHandle and passes its IntPtr to EnumWindows:
  - tokenHandle = GCHandle.Alloc(cancellationToken)
  - tokenHandleParam = GCHandle.ToIntPtr(tokenHandle)
  - NativeMethods.EnumWindows(callbackptr, tokenHandleParam)
- In callback: GCHandle.FromIntPtr(lParam) to get token and if cancellationToken.IsCancellationRequested return false (stop enumeration).

Why
- EnumWindows accepts an IntPtr lParam. Using GCHandle allows passing arbitrary managed state (like CancellationToken) to the callback safely.

2) UWP hosted windows (ApplicationFrameHost correction)
- When a window’s process name is "ApplicationFrameHost.exe", plugin launches a Task that calls EnumChildWindows on that window to find a child window whose class starts with "Windows.UI.Core." and then extracts the child process id and updates the process cache entry so the Window will be attributed to the real UWP app process instead of ApplicationFrameHost.

Why
- UWP apps are hosted by ApplicationFrameHost, so top-level handle process name may be ApplicationFrameHost rather than the real app. The plugin corrects attribution for better display and kill behavior.

3) Close and kill workflows (ContextMenuHelper.cs)
- Close: Action uses Window.CloseThisWindow() which spawns a thread that calls SendMessageTimeout WM_SYSCOMMAND/SC_CLOSE with a 5000ms timeout.
- Kill: Before kill, plugin validates process exists and matches name/ID (Window.Process.DoesExist && Process.Name equals WindowProcess.GetProcessNameFromProcessID(...)). If WindowWalkerSettings.Instance.ConfirmKillProcess is true, the UI shows MessageBox.Show asking confirmation. To kill:
  - If WindowProcess.IsFullAccessDenied: run "taskkill.exe /pid <pid> /f [/t]" via Helper.OpenInShell with Runas elevation.
  - Else: Process.GetProcessById(pid).Kill(killProcessTree)

4) Live preview
- LivePreview.ActivateLivePreview(true, targetWindow, windowToSpare, LivePreviewTrigger.Superbar...) calls DwmpActivateLivePreview to make the target window stand out. LivePreview.DeactivateLivePreview calls DwmpActivateLivePreview(false,...).

---

How plugin filters and decides what to show
- Filters used in OpenWindows.WindowEnumerationCallBack:
  - newWindow.IsWindow && newWindow.Visible && newWindow.IsOwner
  - (!newWindow.IsToolWindow || newWindow.IsAppWindow)
  - !newWindow.TaskListDeleted
  - (newWindow.Desktop.IsVisible || not ResultsFromVisibleDesktopOnly or desktop count < 2)
  - newWindow.ClassName != "Windows.UI.Core.CoreWindow"
  - newWindow.Process.Name != PowerLauncher exe name (to hide the plugin host)
  - Cloak handling: hide if IsCloaked unless GetWindowCloakState() == OtherDesktop

DWM cloak logic:
- DwmGetWindowAttribute(... Cloaked ...) -> switch by DwmWindowCloakStates.* values -> map to Window.WindowCloakState.*; plugin excludes cloaked windows (unless OtherDesktop).

---

Security, elevated processes, and UX decisions
- Plugin detects elevated processes by testing OpenProcess(AllAccess) and checking ERROR_ACCESS_DENIED. If denied:
  - Optionally hide Kill action (WindowWalkerSettings.HideKillProcessOnElevatedProcesses).
  - If Kill requested, plugin uses taskkill.exe launched with RunAs to prompt for elevation when needed.
- Closing windows uses WM_SYSCOMMAND/SC_CLOSE with a timeout rather than force-kill to allow graceful shutdown.

---

Representative PInvoke signatures (examples)
Note: these are typical PInvoke signatures similar to what NativeMethods likely contains.

- EnumWindows
  [DllImport("user32.dll")]
  static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
  delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

- GetWindowTextLength / GetWindowText
  [DllImport("user32.dll", CharSet = CharSet.Auto, SetLastError = true)]
  static extern int GetWindowTextLength(IntPtr hWnd);
  [DllImport("user32.dll", CharSet = CharSet.Auto, SetLastError = true)]
  static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);

- GetClassName
  [DllImport("user32.dll", CharSet = CharSet.Auto, SetLastError = true)]
  static extern int GetClassName(IntPtr hWnd, StringBuilder lpClassName, int nMaxCount);

- GetWindowThreadProcessId
  [DllImport("user32.dll")]
  static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);

- OpenProcess / GetProcessImageFileName
  [DllImport("kernel32.dll", SetLastError = true)]
  static extern IntPtr OpenProcess(ProcessAccessFlags processAccess, bool bInheritHandle, int processId);
  [DllImport("psapi.dll", CharSet = CharSet.Auto)]
  static extern int GetProcessImageFileName(IntPtr hProcess, StringBuilder lpImageFileName, int nSize);

- DwmGetWindowAttribute / DwmSetWindowAttribute
  [DllImport("dwmapi.dll")]
  static extern int DwmGetWindowAttribute(IntPtr hwnd, int dwAttribute, out int pvAttribute, int cbAttribute);
  [DllImport("dwmapi.dll")]
  static extern int DwmSetWindowAttribute(IntPtr hwnd, int dwAttribute, ref uint pvAttribute, int cbAttribute);

- SendMessage / SendMessageTimeout
  [DllImport("user32.dll")]
  static extern IntPtr SendMessage(IntPtr hWnd, uint Msg, IntPtr wParam, IntPtr lParam);
  [DllImport("user32.dll")]
  static extern IntPtr SendMessageTimeout(IntPtr hWnd, uint Msg, IntPtr wParam, IntPtr lParam, uint fuFlags, uint uTimeout, out IntPtr lpdwResult);

- ShowWindow / SetForegroundWindow / FlashWindow
  [DllImport("user32.dll")]
  static extern bool ShowWindow(IntPtr hWnd, ShowWindowCommand nCmdShow);
  [DllImport("user32.dll")]
  static extern bool SetForegroundWindow(IntPtr hWnd);
  [DllImport("user32.dll")]
  static extern bool FlashWindow(IntPtr hWnd, bool bInvert);

---

Where to look in the plugin code (quick map)
- OpenWindows.cs — EnumWindows enumeration, filters, cancellation token handling.
- Window.cs — Title retrieval, style checks (GetWindowLong), visibility, cloak state (DwmGetWindowAttribute), SwitchToWindow (SetForegroundWindow / ShowWindow / SendMessage fallback), CloseThisWindow (SendMessageTimeout), CreateWindowProcessInstance (EnumChildWindows background task).
- WindowProcess.cs — GetProcessIDFromWindowHandle (GetWindowThreadProcessId), GetProcessNameFromProcessID (OpenProcess + GetProcessImageFileName), TestProcessAccessUsingAllAccessFlag (OpenProcess(AllAccess) + GetLastError).
- LivePreview.cs — DwmSetWindowAttribute, NativeMethods.DwmpActivateLivePreview wrapper usage.
- ContextMenuHelper.cs — uses WindowProcess flags to hide Kill option; uses System.Windows.MessageBox.Show for confirmation and calls Window.Process.KillThisProcess.
- ResultHelper.cs — uses Helper.OpenInShell to open Explorer options (not native Win32, but external process invocation).

---

Security & compatibility notes
- Some DWM functions (e.g., DwmpActivateLivePreview) may be undocumented or internal and can change across Windows versions. The plugin ignores return codes for some DWM calls; robust code should check return values and handle failure gracefully.
- OpenProcess(AllAccess) used solely to detect access denied; always close handles.
- The plugin sometimes performs operations on background threads (CloseThisWindowHelper) to avoid blocking UI thread; enumeration callback executes in the EnumWindows caller thread and must not block.

---