"""
Base Publisher Interface.
All platform-specific publishers must implement this interface.
Ensures boundary isolation and MECE adherence in the execution layer.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any


class BasePublisher(ABC):
    def __init__(self, platform_name: str, **kwargs):
        self.platform_name = platform_name

    @abstractmethod
    async def publish(
        self, text: str, media_paths: Optional[List[str]] = None, **kwargs
    ) -> Dict[str, Any]:
        """
        Submits the content to the respective platform or tool.
        Returns a dict containing 'status': 'success'/'failed' and other metadata like 'url' or 'id'.
        """
        pass
