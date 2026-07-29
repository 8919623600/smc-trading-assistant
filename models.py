from dataclasses import dataclass
from datetime import datetime


@dataclass
class SwingPoint:
    time: datetime
    price: float
    swing_type: str  # "HIGH" or "LOW"

    label: str = ""          # HH, HL, LH, LL
    major: bool = False
    liquidity: bool = False
    broken: bool = False
    strength: int = 0
