from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Any


@dataclass
class SwingPoint:
    """
    Represents a swing high or swing low.
    """

    time: datetime
    price: float
    swing_type: str

    label: str = ""
    major: bool = False
    liquidity: bool = False
    broken: bool = False
    strength: int = 0


@dataclass
class AnalysisResult:
    """
    Stores the complete market analysis.
    """

    df: Any
    timeframe: str

    swing_highs: List[SwingPoint] = field(default_factory=list)
    swing_lows: List[SwingPoint] = field(default_factory=list)

    structure: str = ""

    bos: Optional[dict] = None
