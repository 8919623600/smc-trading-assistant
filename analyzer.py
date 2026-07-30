"""
analyzer.py

Market analysis pipeline for BMIE.

Responsibilities
----------------
- Fetch market data
- Detect swings
- Identify major swings
- Analyze market structure
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
from smc.bos import detect_bos
from smc.choch import detect_choch

from models import AnalysisResult


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
    # Swing Detection
    # ======================================================

    swing_highs, swing_lows = find_swings(df)

    # ======================================================
    # Major Swing Detection
    # ======================================================

    major_highs = find_major_swings(swing_highs)
    major_lows = find_major_swings(swing_lows)

    # ======================================================
    # Market Structure
    # ======================================================

    major_highs, major_lows, structure = analyze_structure(
        major_highs,
        major_lows,
    )

    # ======================================================
    # Break of Structure
    # ======================================================

    bos = detect_bos(
        df,
        major_highs,
        major_lows,
    )

    # ======================================================
    # Change of Character
    # ======================================================

    choch = detect_choch(
        df,
        major_highs,
        major_lows,
        structure,
    )

    # ======================================================
    # Return Analysis Result
    # ======================================================

    return AnalysisResult(
        df=df,
        timeframe=timeframe,
        swing_highs=major_highs,
        swing_lows=major_lows,
        structure=structure,
        bos=bos,
        choch=choch,
    )