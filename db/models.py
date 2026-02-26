from dataclasses import dataclass
from typing import List, Optional


@dataclass
class MemoryRecord:
    id: Optional[int]
    content: str
    app_name: str
    agent_id: str
    timestamp: str
    tags: List[str]
    importance_score: float
    metadata_json: str
    encrypted: int = 0
