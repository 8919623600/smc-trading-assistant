"""
smc/major_swings.py

Major Swing Detection

Filters swings that are considered significant enough
to participate in market structure analysis.
"""

from typing import List

from config import MAJOR_SWING_STRENGTH
from models import SwingPoint


def find_major_swings(
    swings: List[SwingPoint],
) -> List[SwingPoint]:
    """
    Return swings whose strength meets the configured threshold.

    Each qualifying swing is marked as a major swing.
    """

    major_swings: List[SwingPoint] = []

    for swing in swings:

        if swing.strength >= MAJOR_SWING_STRENGTH:
            swing.major = True
            major_swings.append(swing)

    return major_swings


def latest_major_swing(
    swings: List[SwingPoint],
):
    """
    Return the most recent major swing.

    Returns None if no major swing exists.
    """

    majors = find_major_swings(swings)

    if not majors:
        return None

    return majors[-1]