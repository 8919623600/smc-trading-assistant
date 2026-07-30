"""
analyzer.py

BMIE Market Analysis Pipeline.

Responsibilities
----------------
- Fetch market data
- Detect swings
- Identify major swings
- Build market structure
- Detect BOS
- Detect CHoCH
- Resolve market state
- Detect Liquidity
- Detect Order Blocks
- Detect Fair Value Gaps

Note:
Trade decision and risk management
are handled after all timeframes are analyzed.

Author: BMIE Project
"""


from config import DEFAULT_BARS

from core.session import TradingSession
from core.analysis_context import AnalysisContext

from fetch_data import get_data


from smc.swings import find_swings
from smc.major_swings import find_major_swings
from smc.structure import analyze_structure

from smc.market_structure import MarketStructureEngine

from smc.bos import BOSEngine
from smc.choch import CHoCHEngine

from smc.state_manager import MarketStateManager

from smc.liquidity import LiquidityEngine

from smc.order_blocks import OrderBlockEngine

from smc.fvg import FVGEngine


from models import (
    AnalysisResult,
    MarketStructure,
)



def analyze_market(
    session: TradingSession,
    timeframe: str,
    bars: int = DEFAULT_BARS,
) -> AnalysisResult:
    """
    Analyze one timeframe.
    """



    # ======================================================
    # Fetch Data
    # ======================================================

    df = get_data(

        session=session,

        timeframe=timeframe,

        bars=bars,
    )



    # ======================================================
    # Market Snapshot
    # ======================================================

    current_price = float(
        df.iloc[-1]["close"]
    )

    current_time = df.index[-1]



    # ======================================================
    # Swing Detection
    # ======================================================

    swing_highs, swing_lows = find_swings(df)



    # ======================================================
    # Major Swings
    # ======================================================

    major_highs = find_major_swings(
        swing_highs
    )


    major_lows = find_major_swings(
        swing_lows
    )



    # ======================================================
    # Legacy Structure
    # ======================================================

    major_highs, major_lows, structure = analyze_structure(

        major_highs,

        major_lows,
    )



    # ======================================================
    # Market Structure Engine
    # ======================================================

    structure_engine = MarketStructureEngine(

        major_highs,

        major_lows,
    )


    state = structure_engine.analyze()



    market_structure = MarketStructure(

        trend=state.trend,

        state=state.state,

        major_high=state.last_high,

        major_low=state.last_low,
    )



    # ======================================================
    # Shared Context
    # ======================================================

    context = AnalysisContext(

        df=df,

        swing_highs=major_highs,

        swing_lows=major_lows,

        market_structure=market_structure,
    )



    # ======================================================
    # BOS
    # ======================================================

    bos_engine = BOSEngine(context)

    bos = bos_engine.analyze()


    market_structure.last_bos = bos



    # ======================================================
    # CHoCH
    # ======================================================

    choch_engine = CHoCHEngine(context)

    choch = choch_engine.analyze()


    market_structure.last_choch = choch



    # ======================================================
    # Market State
    # ======================================================

    state_manager = MarketStateManager(

        market_structure,

        bos,

        choch,
    )


    market_state = state_manager.analyze()



    # ======================================================
    # Liquidity
    # ======================================================

    liquidity_engine = LiquidityEngine(

        context.swing_highs,

        context.swing_lows,
    )


    liquidity = liquidity_engine.analyze()



    # ======================================================
    # Order Blocks
    # ======================================================

    order_block_engine = OrderBlockEngine(

        context.swing_highs,

        context.swing_lows,
    )


    order_blocks = order_block_engine.analyze()



    # ======================================================
    # Fair Value Gap
    # ======================================================

    fvg_engine = FVGEngine(

        context
    )


    fair_value_gaps = fvg_engine.analyze()



    # ======================================================
    # Build Result
    # ======================================================

    result = AnalysisResult(

        df=df,

        timeframe=timeframe,


        current_price=current_price,

        current_time=current_time,


        swing_highs=major_highs,

        swing_lows=major_lows,


        structure=structure,


        market_structure=market_structure,


        bos=bos,

        choch=choch,


        liquidity=liquidity,


        order_blocks=order_blocks,


        fair_value_gaps=fair_value_gaps,
    )



    # Attach state internally

    result.market_state = market_state



    return result