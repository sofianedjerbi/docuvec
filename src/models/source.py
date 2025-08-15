"""Source data model"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class Source:
    """Data class for certification source"""
    id: str
    url: str
    title: str
    tags: Dict[str, Any]