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

    last_bos: Optional[dict] = None

    last_choch: Optional[dict] = None

    major_high: Optional[SwingPoint] = None

    major_low: Optional[SwingPoint] = None


# ==========================================================
# Analysis Result
# ==========================================================

@dataclass
class AnalysisResult:
    df: Any
    timeframe: str

    swing_highs: List[SwingPoint] = field(default_factory=list)
    swing_lows: List[SwingPoint] = field(default_factory=list)

    # Legacy field (kept for compatibility)
    structure: str = ""

    # New Market Structure object
    market_structure: Optional[MarketStructure] = None

    bos: Optional[dict] = None

    choch: Optional[dict] = None

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