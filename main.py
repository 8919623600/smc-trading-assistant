from analyzer import analyze_market
from charts.plot_chart import plot_chart


def main():

    result = analyze_market()

    df = result["df"]
    swing_highs = result["swing_highs"]
    swing_lows = result["swing_lows"]
    structure = result["structure"]
    bos = result["bos"]

    plot_chart(
        df,
        swing_highs,
        swing_lows,
        filename="XAUUSD_15m.png",
    )

    print("=" * 80)
    print("SMART MONEY CONCEPT ANALYZER")
    print("=" * 80)

    print(f"Symbol         : {df.iloc[-1]['symbol']}")
    print(f"Timeframe      : {result['timeframe']}")
    print(f"Current Price  : {df.iloc[-1]['close']:.2f}")

    print("\nOVERALL STRUCTURE")
    print("-" * 80)
    print(structure)

    print("\nBREAK OF STRUCTURE")
    print("-" * 80)

    if bos["direction"]:
        print(f"Direction : {bos['direction']}")
        print(f"Level     : {bos['level']:.2f}")
        print(f"Time      : {bos['time']}")
    else:
        print("No confirmed BOS detected.")

    print("=" * 80)


if __name__ == "__main__":
    main()
