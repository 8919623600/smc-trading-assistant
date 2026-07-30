from analyzer import analyze_market
from charts.plot_chart import plot_chart


def main():
    """
    Main entry point of the Smart Money Concept Analyzer.
    """

    # Run market analysis
    result = analyze_market()

    # Plot chart
    plot_chart(
        result.df,
        result.swing_highs,
        result.swing_lows,
        filename="XAUUSD_15m.png",
    )

    # Print Summary
    print("=" * 80)
    print("SMART MONEY CONCEPT ANALYZER")
    print("=" * 80)

    print(f"Timeframe      : {result.timeframe}")
    print(f"Current Price  : {result.df.iloc[-1]['close']:.2f}")

    print("\nMARKET STRUCTURE")
    print("-" * 80)
    print(result.structure)

    print("\nBREAK OF STRUCTURE")
    print("-" * 80)

    if result.bos and result.bos["direction"]:
        print(f"Direction : {result.bos['direction']}")
        print(f"Level     : {result.bos['level']:.2f}")
        print(f"Time      : {result.bos['time']}")
    else:
        print("No confirmed BOS detected.")

    print("=" * 80)


if __name__ == "__main__":
    main()
