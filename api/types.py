# api/types.py
from dataclasses import dataclass
from typing import Callable, Optional

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
    icon_path: Optional[str] = None # Path to icon or None
    action: Optional[Action] = None
    score: int = 0  # For sorting results from multiple extensions