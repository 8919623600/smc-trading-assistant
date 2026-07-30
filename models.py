from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List, Optional


# ==========================================================
# Swing Point
# ==========================================================

@dataclass
class SwingPoint:
    time: datetime
    price: float
    swing_type: str

    label: str = ""
    major: bool = False
    liquidity: bool = False
    broken: bool = False
    strength: int = 0


# ==========================================================
# Market Events
# ==========================================================

@dataclass
class MarketEvent:
    """
    Base class for all market events.
    """

    direction: Optional[str] = None
    level: Optional[float] = None
    time: Optional[datetime] = None
    confirmed: bool = False


@dataclass
class BOSEvent(MarketEvent):
    """
    Break of Structure event.
    """
    pass


@dataclass
class CHoCHEvent(MarketEvent):
    """
    Change of Character event.
    """
    pass


# ==========================================================
# Market Structure
# ==========================================================

@dataclass
class MarketStructure:
    """
    Represents the current market structure.

    This class will gradually become the single source
    of truth for BMIE's SMC engine.
    """

    trend: str = "Sideways"

    state: str = "Unknown"

    last_bos: BOSEvent = field(default_factory=BOSEvent)

    last_choch: CHoCHEvent = field(default_factory=CHoCHEvent)

    major_high: Optional[SwingPoint] = None

    major_low: Optional[SwingPoint] = None


# ==========================================================
# Analysis Result
# ==========================================================

@dataclass
class AnalysisResult:
    """
    Result of analyzing a single timeframe.
    """

    # Raw market data
    df: Any

    timeframe: str

    # Current market snapshot
    current_price: float = 0.0

    current_time: Optional[datetime] = None

    # Swing data
    swing_highs: List[SwingPoint] = field(default_factory=list)

    swing_lows: List[SwingPoint] = field(default_factory=list)

    # Legacy field (kept for compatibility)
    structure: str = ""

    # New Market Structure object
    market_structure: Optional[MarketStructure] = None

    # Market Events
    bos: BOSEvent = field(default_factory=BOSEvent)

    choch: CHoCHEvent = field(default_factory=CHoCHEvent)

    # Future SMC Components
    liquidity: List[Any] = field(default_factory=list)

    order_blocks: List[Any] = field(default_factory=list)

    fair_value_gaps: List[Any] = field(default_factory=list)

    supply_zones: List[Any] = field(default_factory=list)

    demand_zones: List[Any] = field(default_factory=list)

    confidence: float = 0.0


# ==========================================================
# Multi-Timeframe Analysis
# ==========================================================

@dataclass
class MarketAnalysis:
    bias: Optional[AnalysisResult] = None

    structure: Optional[AnalysisResult] = None

    trend: Optional[AnalysisResult] = None

    setup: Optional[AnalysisResult] = None

    entry: Optional[AnalysisResult] = None

    def as_dict(self):
        return {
            "bias": self.bias,
            "structure": self.structure,
            "trend": self.trend,
            "setup": self.setup,
            "entry": self.entry,
        }