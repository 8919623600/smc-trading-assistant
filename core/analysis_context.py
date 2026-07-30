"""
core/analysis_context.py

Shared analysis context passed between BMIE SMC engines.

Responsibilities
----------------
- Store common market data
- Store swing information
- Store market structure
- Store structural events (BOS / CHoCH)

Author: BMIE Project
"""

from dataclasses import dataclass, field
from typing import Any, List

from models import (
    SwingPoint,
    MarketStructure,
    BOSEvent,
    CHoCHEvent,
)


@dataclass
class AnalysisContext:
    """
    Shared analysis context passed between SMC engines.

    Created by analyzer.py and consumed by:
        - BOSEngine
        - CHoCHEngine
        - LiquidityEngine
        - OrderBlockEngine
        - Future SMC engines
    """


    # ======================================================
    # Raw Market Data
    # ======================================================

    df: Any


    # ======================================================
    # Swing Data
    # ======================================================

    swing_highs: List[SwingPoint] = field(
        default_factory=list
    )

    swing_lows: List[SwingPoint] = field(
        default_factory=list
    )


    # ======================================================
    # Market Structure
    # ======================================================

    market_structure: MarketStructure = field(
        default_factory=MarketStructure
    )


    # ======================================================
    # Structural Events
    # ======================================================

    bos: BOSEvent = field(
        default_factory=BOSEvent
    )

    choch: CHoCHEvent = field(
        default_factory=CHoCHEvent
    )