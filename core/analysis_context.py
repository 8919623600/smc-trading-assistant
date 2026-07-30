from dataclasses import dataclass, field
from typing import Any, List

from models import SwingPoint, MarketStructure


@dataclass
class AnalysisContext:
    """
    Shared analysis context passed between SMC engines.

    This object contains the common inputs required during
    market analysis. It is created by the Analyzer and
    passed to each engine as needed.

    Note:
        This is an internal working object and should not be
        returned outside the analysis pipeline.
    """

    # Raw market data
    df: Any

    # Swing data
    swing_highs: List[SwingPoint] = field(default_factory=list)
    swing_lows: List[SwingPoint] = field(default_factory=list)

    # Market structure
    market_structure: MarketStructure = field(default_factory=MarketStructure)