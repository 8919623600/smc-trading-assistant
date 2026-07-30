"""
models.py

Core data models used throughout the Balaji Market Intelligence
Engine (BMIE).

Author: BMIE Project
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List, Optional


# ==========================================================
# Swing Point
# ==========================================================

@dataclass
class SwingPoint:
    """
    Represents a market swing high or swing low.
    """

    time: datetime
    price: float
    swing_type: str

    label: str = ""
    major: bool = False
    liquidity: bool = False
    broken: bool = False
    strength: int = 0


# ==========================================================
# Analysis Result
# ==========================================================

@dataclass
class AnalysisResult:
    """
    Stores the complete analysis result for a single timeframe.
    """

    # Raw OHLC Data
    df: Any

    # Timeframe
    timeframe: str

    # Swing Information
    swing_highs: List[SwingPoint] = field(default_factory=list)
    swing_lows: List[SwingPoint] = field(default_factory=list)

    # Market Structure
    structure: str = ""

    # Break Of Structure
    bos: Optional[dict] = None

    # Future Features (kept for forward compatibility)
    choch: Optional[dict] = None
    liquidity: List[Any] = field(default_factory=list)
    order_blocks: List[Any] = field(default_factory=list)
    fair_value_gaps: List[Any] = field(default_factory=list)
    supply_zones: List[Any] = field(default_factory=list)
    demand_zones: List[Any] = field(default_factory=list)

    # Confidence Score
    confidence: float = 0.0


# ==========================================================
# Multi-Timeframe Analysis
# ==========================================================

@dataclass
class MarketAnalysis:
    """
    Holds the complete multi-timeframe analysis.

    This class is not yet used by the application but will
    become the standard return object in future versions.
    """

    bias: Optional[AnalysisResult] = None
    structure: Optional[AnalysisResult] = None
    trend: Optional[AnalysisResult] = None
    setup: Optional[AnalysisResult] = None
    entry: Optional[AnalysisResult] = None

    def as_dict(self):
        """
        Return analyses as a dictionary.
        """

        return {
            "bias": self.bias,
            "structure": self.structure,
            "trend": self.trend,
            "setup": self.setup,
            "entry": self.entry,
        }