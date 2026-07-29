from config import DEFAULT_TIMEFRAME, DEFAULT_BARS
from fetch_data import get_data
from strategy.swings import find_swings
from strategy.structure import analyze_structure
from strategy.bos import detect_bos


def analyze_market(
    timeframe=DEFAULT_TIMEFRAME,
    bars=DEFAULT_BARS,
):
    """
    Runs the complete market analysis.
    """

    df = get_data(timeframe, bars)

    swing_highs, swing_lows = find_swings(df)

    swing_highs, swing_lows, structure = analyze_structure(
        swing_highs,
        swing_lows,
    )

    bos = detect_bos(
        df,
        swing_highs,
        swing_lows,
    )

    return {
        "df": df,
        "timeframe": timeframe,
        "swing_highs": swing_highs,
        "swing_lows": swing_lows,
        "structure": structure,
        "bos": bos,
    }
