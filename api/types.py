# api/types.py
from dataclasses import dataclass, field
from typing import Callable, Optional, Any, List

@dataclass
class Action:
    """Defines what happens when a user hits Enter."""
    name: str
    handler: Callable[[], None]
    close_on_action: bool = True

@dataclass
class ResultItem:
    """Standardized result object."""
    id: str
    name: str
    description: str = ""
    icon_path: Optional[str] = None 
    action: Optional[Action] = None
    score: int = 0
    
    # List of available actions for the Context Menu
    context_actions: List[Action] = field(default_factory=list)
    
    # --- UI CUSTOMIZATION ---
    widget_factory: Optional[Callable[[], Any]] = None 
    # Custom height for this item (default is 64)
    height: int = 64