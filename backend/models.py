from typing import Dict, List

class SetbackDTO(dict):
    heatOffset: float
    coolOffset: float
    schedule: Dict[str, List[dict]]