from services.volatility import estimate_iv, get_historical_volatility

# Test with Apple
ticker = "AAPL"
strike = 200.0
time_to_expiry = 0.5  # 6 months
is_call = True

# Estimate IV
iv = estimate_iv(ticker, strike, time_to_expiry, is_call)
print(f"Estimated IV for {ticker}: {iv:.4f} ({iv*100:.2f}%)")

# Get historical volatility
hv = get_historical_volatility(ticker)
if hv:
    print(f"Historical volatility for {ticker}: {hv:.4f} ({hv*100:.2f}%)")
else:
    print(f"Could not calculate historical volatility for {ticker}")