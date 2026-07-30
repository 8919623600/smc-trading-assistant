"""
analyzer.py

Market analysis pipeline for BMIE.

Responsibilities
----------------
- Fetch market data
- Detect swings
- Identify major swings
- Build market structure
- Detect Break of Structure (BOS)
- Detect Change of Character (CHoCH)

Author: BMIE Project
"""

from config import DEFAULT_BARS
from core.session import TradingSession
from fetch_data import get_data

from smc.swings import find_swings
from smc.major_swings import find_major_swings
from smc.structure import analyze_structure
from smc.market_structure import MarketStructureEngine
from smc.bos import detect_bos
from smc.choch import detect_choch

from models import AnalysisResult, MarketStructure


def analyze_market(
    session: TradingSession,
    timeframe: str,
    bars: int = DEFAULT_BARS,
) -> AnalysisResult:
    """
    Perform complete SMC analysis for a timeframe.
    """

    # ======================================================
    # Fetch Market Data
    # ======================================================

    df = get_data(
        session=session,
        timeframe=timeframe,
        bars=bars,
    )

    # ======================================================
    # Market Snapshot
    # ======================================================

    current_price = float(df.iloc[-1]["close"])
    current_time = df.index[-1]

    # ======================================================
    # Detect Swings
    # ======================================================

    swing_highs, swing_lows = find_swings(df)

    # ======================================================
    # Filter Major Swings
    # ======================================================

    major_highs = find_major_swings(swing_highs)
    major_lows = find_major_swings(swing_lows)

    # ======================================================
    # Legacy Structure (kept for compatibility)
    # ======================================================

    major_highs, major_lows, structure = analyze_structure(
        major_highs,
        major_lows,
    )

    # ======================================================
    # Market Structure Engine
    # ======================================================

    engine = MarketStructureEngine(
        major_highs,
        major_lows,
    )

    state = engine.analyze()

    market_structure = MarketStructure(
        trend=state.trend,
        state=state.state,
        major_high=state.last_high,
        major_low=state.last_low,
    )

    # ======================================================
    # Break of Structure (BOS)
    # ======================================================

    bos = detect_bos(
        df,
        major_highs,
        major_lows,
    )

    market_structure.last_bos = bos

    # ======================================================
    # Change of Character (CHoCH)
    # ======================================================

    choch = detect_choch(
        df,
        major_highs,
        major_lows,
        structure,
    )

    market_structure.last_choch = choch

    # ======================================================
    # Build Analysis Result
    # ======================================================

    return AnalysisResult(
        df=df,
        timeframe=timeframe,
        current_price=current_price,
        current_time=current_time,
        swing_highs=major_highs,
        swing_lows=major_lows,
        structure=structure,                # Backward compatibility
        market_structure=market_structure,  # New Market Structure Engine
        bos=bos,
        choch=choch,
    )