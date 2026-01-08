# NeverLiie

A lightweight, extensible productivity launcher for Windows with an extension architecture. Access applications, tools, and utilities through a global hotkey-driven interface.

## Features

- **Global Hotkey Launcher**: Activate the launcher with a global keyboard shortcut (Alt+Space)
- **System Tray Integration**: Minimize to system tray with quick access
- **Extension System**: Extensible architecture for adding custom functionality
- **Settings Management**: Configure extensions and preferences through a settings UI
- **Built-in Extensions**:
  - **AI Assistant**: Integration with Gemini API for AI-powered queries
  - **Calculator**: Quick calculator functionality
  - **Clipboard Manager**: Clipboard history and management
  - **File Search**: Quick file search across your system
  - **System Apps**: Access to system applications and windows

## Project Structure

```
NeverLiie/
├── main.py                          # Application entry point
├── settings.json                    # Configuration file
├── api/                            # Extension API
│   ├── context.py                  # Extension context
│   ├── extension.py                # Base extension class
│   └── types.py                    # Type definitions
├── core/                           # Core application logic
│   ├── app.py                      # Main application class
│   ├── extension_manager.py       # Extension loader
│   ├── settings.py                 # Settings management
│   ├── settings_ui.py              # Settings interface
│   ├── ui.py                       # UI components
│   └── win32_utils.py              # Windows API utilities
└── extensions/                     # Installed extensions
    ├── ai/                         # AI assistant extension
    ├── calculator/                 # Calculator extension
    ├── clipboard/                  # Clipboard manager
    ├── file_search/                # File search extension
    └── system_apps/                # System applications access
```

## Requirements

- Python 3.8+
- Windows 10/11
- PySide6
- Google Generative AI API key (for AI extension)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/NeverLiie.git
cd NeverLiie
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure settings:
   - Edit `settings.json` with your API keys and preferences
   - Add your Google Generative AI API key for the AI extension

4. Run the application:
```bash
python main.py
```

## Usage

### Launching

- **Hotkey**: Press `Alt+Space` to open the launcher
- **Tray Icon**: Click the system tray icon to access the launcher

### Extensions

#### AI Assistant
- Query the Gemini 2.5 Flash model
- Requires API key in settings.json

#### Calculator
- Quick calculations
- Basic arithmetic operations

#### Clipboard Manager
- View clipboard history
- Quick access to recent items
- Media clipboard support

#### File Search
- Search for files on your system
- Fast indexed search

#### System Apps
- Quick access to installed applications
- Window management shortcuts

## Configuration

Edit `settings.json` to configure:

```json
{
  "disabled_extensions": [],
  "extension_settings": {
    "ai": {
      "api_key": "YOUR_API_KEY",
      "model_name": "gemini-2.5-flash"
    }
  }
}
```

## Creating Custom Extensions

Extensions are loaded from the `extensions/` directory. Each extension should:

1. Create a subdirectory with the extension name
2. Include an `__init__.py` file that exports an `Extension` subclass
3. Implement required methods from the `Extension` API

Example extension structure:
```
extensions/myextension/
├── __init__.py
└── __pycache__/
```

## Development

### Key Components

- **App** (`core/app.py`): Main application class managing lifecycle, hotkeys, and UI
- **ExtensionManager** (`core/extension_manager.py`): Dynamically loads extensions from disk
- **Extension** (`api/extension.py`): Base class for all extensions
- **SettingsManager** (`core/settings.py`): Handles configuration persistence

### Win32 Integration

The application uses Windows API for:
- Global hotkey registration
- Window focus management
- System tray integration

See `windowwalker_implementation_windows_api_documentation.md` for detailed API documentation.

## License

[Your License Here]

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
