# Generate Dummy Data for Testing
def make_dummy_data(rows, start_price=4050.0):
    times = pd.date_range(end=datetime.now(), periods=rows, freq='1min')
    np.random.seed(42)
    closes = start_price + np.cumsum(np.random.randn(rows))
    return pd.DataFrame({
        'open': closes - 0.5,
        'high': closes + 1.5,
        'low': closes - 1.5,
        'close': closes
    }, index=times)

# Test Runner
engine = SMCTradingEngine(min_rr=2.0, atr_multiplier=1.0)

data = {
    '4H': make_dummy_data(100),
    '1H': make_dummy_data(100),
    '15M': make_dummy_data(100),
    '1M': make_dummy_data(100)
}

result = engine.analyze(data)
print("=== SMC ANALYSIS RESULT ===")
print(result)