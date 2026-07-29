import os
import mplfinance as mpf
import pandas as pd


def plot_chart(df, swing_highs, swing_lows, filename="xauusd_chart.png"):
    """
    Plot candlestick chart with swing markers and labels.
    """

    os.makedirs("charts/output", exist_ok=True)

    df_plot = df.copy()

    high_series = pd.Series(index=df_plot.index, dtype=float)
    low_series = pd.Series(index=df_plot.index, dtype=float)

    for swing in swing_highs:
        if swing.time in high_series.index:
            high_series.loc[swing.time] = swing.price

    for swing in swing_lows:
        if swing.time in low_series.index:
            low_series.loc[swing.time] = swing.price

    addplots = [
        mpf.make_addplot(
            high_series,
            type="scatter",
            marker="^",
            markersize=80,
        ),
        mpf.make_addplot(
            low_series,
            type="scatter",
            marker="v",
            markersize=80,
        ),
    ]

    fig, axes = mpf.plot(
        df_plot,
        type="candle",
        style="yahoo",
        volume=False,
        addplot=addplots,
        figsize=(16, 8),
        returnfig=True,
    )

    ax = axes[0]

    # Label swing highs
    for swing in swing_highs:
        ax.annotate(
            f"{swing.label} ({swing.strength})",
            xy=(swing.time, swing.price),
            xytext=(0, 12),
            textcoords="offset points",
            fontsize=8,
            ha="center",
        )

    # Label swing lows
    for swing in swing_lows:
        ax.annotate(
            f"{swing.label} ({swing.strength})",
            xy=(swing.time, swing.price),
            xytext=(0, -18),
            textcoords="offset points",
            fontsize=8,
            ha="center",
        )

    output_path = f"charts/output/{filename}"
    fig.savefig(output_path, dpi=150, bbox_inches="tight")

    print(f"\nChart saved to {output_path}")
