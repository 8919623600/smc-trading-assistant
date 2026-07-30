"""
core/market_context.py

Central market context for BMIE.

The MarketContext object represents the complete
understanding of the market for a single timeframe.

Every SMC module updates this object instead of
passing independent objects through the pipeline.

Author: BMIE Project
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from models import (
    SwingPoint,
    BOSEvent,
    CHoCHEvent,
    MarketStructure,
)


# ==========================================================
# Market Context
# ==========================================================

@dataclass
class MarketContext:
    """
    Single source of truth for one timeframe.
    """

    # ------------------------------------------------------
    # Market Snapshot
    # ------------------------------------------------------

    timeframe: str = ""

    current_price: float = 0.0

    current_time: Optional[datetime] = None

    # ------------------------------------------------------
    # Structure
    # ------------------------------------------------------

    structure: str = ""

    market_structure: Optional[MarketStructure] = None

    # ------------------------------------------------------
    # Swings
    # ------------------------------------------------------

    swing_highs: List[SwingPoint] = field(default_factory=list)

    swing_lows: List[SwingPoint] = field(default_factory=list)

    # ------------------------------------------------------
    # Events
    # ------------------------------------------------------

    bos: BOSEvent = field(default_factory=BOSEvent)

    choch: CHoCHEvent = field(default_factory=CHoCHEvent)

    # ------------------------------------------------------
    # SMC Components
    # ------------------------------------------------------

    liquidity: list = field(default_factory=list)

    order_blocks: list = field(default_factory=list)

    fair_value_gaps: list = field(default_factory=list)

    supply_zones: list = field(default_factory=list)

    demand_zones: list = field(default_factory=list)

    # ------------------------------------------------------
    # Decision Support
    # ------------------------------------------------------

    confidence: float = 0.0

    recommendation: str = "WAIT"

    reason: str = ""