# Extensions

This directory contains extensions for NeverLiie. Extensions provide additional functionality like file search, calculator, system apps, and more.

## How Extensions Work

Extensions are Python modules that:
1. Inherit from the `Extension` base class
2. Are automatically discovered and loaded from subdirectories
3. Respond to search queries via the `on_input()` method
4. Return `ResultItem` objects that appear in the launcher UI
5. Can optionally provide custom widgets and settings panels

## Core API

### Extension Base Class

Every extension must inherit from `api.extension.Extension`:

```python
from api.extension import Extension

class MyExtension(Extension):
    def __init__(self, context):
        super().__init__(context)
        # Your initialization code here
```

#### Required Methods

**`on_input(text: str) -> List[ResultItem]`**

Called whenever user types in the launcher. Returns a list of search results.

```python
def on_input(self, text: str) -> List[ResultItem]:
    if not text:
        return []
    
    # Process input and return results
    return [ResultItem(...)]
```

#### Optional Methods

**`get_extension_view(parent_window: QWidget) -> Optional[QWidget]`**

Return a custom QWidget to display in the launcher (e.g., chat interface, calculator preview).

```python
def get_extension_view(self, parent_window: QWidget) -> Optional[QWidget]:
    return MyCustomWidget(parent_window)
```

**`get_settings_widget() -> Optional[QWidget]`**

Return a QWidget for the Settings window.

```python
def get_settings_widget(self) -> Optional[QWidget]:
    return MySettingsWidget()
```

**`cleanup()`**

Called when extension is being unloaded or reloaded. Clean up resources here.

```python
def cleanup(self):
    # Close connections, stop timers, etc.
    pass
```

### ExtensionContext

The context object provides safe access to core functionality:

```python
# Settings (persistent per-extension)
self.context.get_setting(key, default)
self.context.set_setting(key, value)

# Window control
self.context.hide_window()
self.context.show_window()
self.context.refresh_ui()

# Extension data directory (for databases, cache, etc.)
self.context.data_path  # Path to %APPDATA%/NeverLiie/extensions/your_ext_id

# Extension ID
self.context._ext_id     # Your extension's folder name
```

## Types

### ResultItem

Standardized search result object:

```python
@dataclass
class ResultItem:
    id: str                              # Unique identifier
    name: str                            # Display name (title)
    description: str = ""                # Subtitle/details
    icon_path: Optional[str] = None      # Path to icon file
    action: Optional[Action] = None      # Primary action (Enter key)
    score: int = 0                       # Relevance score (higher = top)
    context_actions: List[Action] = []   # Right-click menu actions
    widget_factory: Callable = None      # Custom UI for this result
    height: int = 64                     # Item height in pixels
```

### Action

Defines what happens when a user triggers an action:

```python
@dataclass
class Action:
    name: str                 # Display name
    handler: Callable[[], None] # Function to execute
    close_on_action: bool = True # Close launcher after action
```

Example:
```python
def open_file():
    os.startfile("C:\\path\\to\\file.txt")

action = Action(
    name="Open",
    handler=open_file,
    close_on_action=True
)
```

## Creating a New Extension

### 1. Create Directory Structure

```
extensions/
└── my_extension/
    ├── __init__.py          # Main extension code
    └── config.py            # (optional) Helper modules
```

### 2. Write the Extension

In `extensions/my_extension/__init__.py`:

```python
from api.extension import Extension
from api.types import ResultItem, Action

class MyExtension(Extension):
    def __init__(self, context):
        super().__init__(context)
        # Load settings, initialize databases, etc.
        self.data_dir = context.data_path
        
    def on_input(self, text: str):
        if not text:
            return []
        
        results = []
        
        # Search logic here
        for item in self.search(text):
            results.append(ResultItem(
                id=item['id'],
                name=item['name'],
                description=item.get('description', ''),
                action=Action(
                    name="Open",
                    handler=lambda: self.open_item(item),
                    close_on_action=True
                ),
                score=item['score']
            ))
        
        return results

# Export the extension class
Extension = MyExtension
```

**Important:** The class must be exported as `Extension` at module level.

## Extension Lifecycle

1. **Discovery:** ExtensionManager scans `extensions/` for subdirectories with `__init__.py`
2. **Loading:** Each module is imported dynamically
3. **Instantiation:** The `Extension` class is instantiated with an `ExtensionContext`
4. **Runtime:** `on_input()` is called on every keystroke (in parallel thread pool)
5. **Shutdown:** `cleanup()` is called if defined

## Reloading

Extensions can be hot-reloaded without restarting the app:
```python
# From ExtensionManager (external)
extension_manager.reload_extension("your_ext_id")
```

## Async Search

Extensions are queried concurrently in a thread pool (10 workers). This keeps the UI responsive even with slow extensions.

- Each extension runs in isolation
- If an extension crashes, it won't affect others
- Results are aggregated and sorted by score in real-time
- Slow queries (>200ms) are logged to console

## Examples

### Simple Text Search

```python
class SimpleExtension(Extension):
    def __init__(self, context):
        super().__init__(context)
        self.items = ["Apple", "Banana", "Cherry"]
    
    def on_input(self, text):
        if not text:
            return []
        
        matches = [item for item in self.items if text.lower() in item.lower()]
        
        return [ResultItem(
            id=item,
            name=item,
            description=f"Found '{item}'",
            score=100
        ) for item in matches]
```

### Custom Widget

```python
class CalculatorWidget(QWidget):
    def __init__(self, expression, result):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.addWidget(QLabel(f"{expression} = {result}"))

class CalculatorExtension(Extension):
    def on_input(self, text):
        result = self.calculate(text)
        
        def make_widget():
            return CalculatorWidget(text, result)
        
        return [ResultItem(
            id="calc",
            name=str(result),
            description=f"Result of {text}",
            widget_factory=make_widget,
            height=80
        )]
```

### Multiple Actions

```python
def open_item():
    os.startfile(item['path'])

def show_properties():
    os.system(f'properties "{item["path"]}"')

result = ResultItem(
    id=item['id'],
    name=item['name'],
    description=item['path'],
    action=Action("Open", open_item),
    context_actions=[
        Action("Open", open_item),
        Action("Properties", show_properties)
    ]
)
```

### Settings

```python
def on_input(self, text):
    enabled = self.get_setting("enabled", True)
    if not enabled:
        return []
    
    # Normal search logic...

def get_settings_widget(self):
    widget = QWidget()
    layout = QVBoxLayout(widget)
    
    checkbox = QCheckBox("Enable Extension")
    checkbox.setChecked(self.get_setting("enabled", True))
    checkbox.stateChanged.connect(
        lambda s: self.set_setting("enabled", s == Qt.Checked)
    )
    
    layout.addWidget(checkbox)
    return widget
```

## Best Practices

1. **Score wisely:** Use meaningful scores. Higher scores appear first. Consider:
   - 1000+: Exact matches
   - 500-999: Strong partial matches
   - 100-499: Weak matches
   - <100: Low relevance

2. **Filter early:** Return `[]` quickly if input doesn't match your extension's purpose

3. **Limit results:** Return 10-20 results max to maintain UI performance

4. **Handle errors gracefully:** Wrap code in try/except, log to console

5. **Use caching:** Cache expensive operations in instance variables

6. **Thread safety:** Extension methods run in worker threads, avoid UI operations in `on_input()`

7. **Respect settings:** Check if extension is enabled before heavy operations

8. **Clean resources:** Implement `cleanup()` to close connections, stop timers, etc.

## Data Persistence

Each extension gets its own data directory:

```python
# Windows: %APPDATA%\NeverLiie\extensions\your_ext_id
# Linux: ~/.local/share/NeverLiie/extensions/your_ext_id

self.context.data_path  # Use this for databases, cache, configs
```

Use `self.get_setting()` and `self.set_setting()` for simple key-value storage.

## Reloading

Extensions can be hot-reloaded without restarting the app:
```python
# From ExtensionManager (external)
extension_manager.reload_extension("your_ext_id")
```

The manager will:
1. Unload the module and submodules
2. Call `cleanup()` on the old instance
3. Re-import and re-instantiate the extension

## Existing Extensions

- **calculator:** Math evaluation with custom preview widget
- **file_search:** File search using Everything SDK (Windows)
- **system_apps:** Windows applications and window search
- **clipboard:** Clipboard history (placeholder)
- **ai:** AI integration (placeholder)

Study these for more examples.
