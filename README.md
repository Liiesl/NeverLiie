# NeverLiie

**A highly opinionated, custom desktop environment for Windows.**

This repository serves as the central documentation and meta-repository for the NeverLiie suite. It allows me to track the state of the entire ecosystem.

### ⚠️ Disclaimer
This project is built for **me**. It is designed around my specific workflow, keybindings, and aesthetic preferences. While you are welcome to clone, fork, and use these tools, do not expect generic features or support for workflows that contradict the core design philosophy.

## Why this exists

Windows, in its default state, is frustrating. While there are polished alternatives for specific tools (PowerToys, Wezterm, MyDockFInder) and full shell replacements (like Seelen UI or Cairoshell), I found myself in an awkward middle ground:

1.  **Existing tools didn't fit:** Most Windows launchers feels Heavy compared to Raycast (macOS) or Rofi (Linux).
2.  **Full replacements are too heavy:** I don't want to replace the low-level window manager or risk system instability by killing `explorer.exe` entirely.

NeverLiie is a collection of standalone tools designed to replace or enhance the specific UI elements I interact with hundreds of times a day: the application launcher, the terminal, and the system tray.

## Components

The suite consists of three distinct repositories. Click the folders above or the links below to view the source code for each.

| Component | Description |
| :--- | :--- |
| **[NeverLiieLauncher](./launcher)** | A keyboard-centric application launcher and command palette. Similar to Alfred or Raycast, but tightly integrated with Windows APIs. |
| **[NeverLiieTerm](./terminal)** | A native Windows terminal multiplexer and remote client. Built for convinience. |
| **[NeverLiieStatusBar](./statusbar)** | A custom replacement for the Windows taskbar status area. |

## Installation & Setup

To clone this entire suite including all submodules:

```bash
git clone --recursive https://github.com/YOUR_USERNAME/NeverLiie.git
```

If you have already cloned the repo without the `--recursive` flag, run:

```bash
git submodule update --init --recursive
```

### 1. Setting up the Launcher
*   Navigate to the `launcher` directory.
*   Follow the build instructions in that specific repository.
*   **Recommendation:** Disable the default Windows Start Menu key binding to map the `Win` key (or `Alt+Space`) directly to NeverLiieLauncher.

### 2. Setting up the Terminal
*   Navigate to the `terminal` directory.
*   Build and install the binary.
*   **Integration:** Set `NeverLiieTerm` as your default terminal handler in Windows Settings > Privacy & security > For developers > Terminal.

### 3. Setting up the Taskbar (Windhawk Integration)
Since `NeverLiieStatusBar` is a standalone overlay, you need to hide or modify the native Windows taskbar for the best experience.

I rely on **[Windhawk](https://windhawk.net/)** for the low-level modifications required to make this work cleanly without breaking Windows updates.

**Required Configuration:**
1.  Install Windhawk.
2.  Install the "Taskbar Styler" mod (or your specific custom mod).
3.  Configure the mod to hide the native tray area or the entire taskbar, depending on your preference.
4.  Launch `NeverLiieStatusBar` to fill the void.

## Contributing

As stated, this is a personal project. However, if you find a bug or have a performance improvement that aligns with the current design goals, feel free to open a Pull Request on the specific component repository.

Feature requests that fundamentally change the opinionated nature of the workflow will likely be rejected.