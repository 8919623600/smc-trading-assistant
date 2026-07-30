def analyze_structure(swing_highs, swing_lows):
    """
    Label swing highs and lows as HH, LH, HL, LL.
    """

    previous_high = None
    previous_low = None

    # Label highs
    for swing in swing_highs:

        if previous_high is None:
            swing.label = "START"

        elif swing.price > previous_high:
            swing.label = "HH"

        elif swing.price < previous_high:
            swing.label = "LH"

        else:
            swing.label = "EH"

        previous_high = swing.price

    # Label lows
    for swing in swing_lows:

        if previous_low is None:
            swing.label = "START"

        elif swing.price > previous_low:
            swing.label = "HL"

        elif swing.price < previous_low:
            swing.label = "LL"

        else:
            swing.label = "EL"

        previous_low = swing.price

    structure = "Sideways"

    if len(swing_highs) >= 2 and len(swing_lows) >= 2:

        last_high = swing_highs[-1].label
        last_low = swing_lows[-1].label

        if last_high == "HH" and last_low == "HL":
            structure = "Bullish"

        elif last_high == "LH" and last_low == "LL":
            structure = "Bearish"

    return swing_highs, swing_lows, structure
