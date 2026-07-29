from config import MAJOR_SWING_STRENGTH


def find_major_swings(swings):
    """
    Filter major swings based on strength.

    Returns only swings that have enough strength.
    """

    major_swings = []

    for swing in swings:

        if swing.strength >= MAJOR_SWING_STRENGTH:
            swing.major = True
            major_swings.append(swing)

    return major_swings
