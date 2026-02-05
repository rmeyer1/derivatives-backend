from services.black_scholes import black_scholes_option_price, greeks

# Test parameters
spot = 100
strike = 105
time_to_expiry = 0.5  # 6 months
risk_free_rate = 0.04  # 4%
volatility = 0.3  # 30%
option_type = 'call'

# Calculate option price
price = black_scholes_option_price(spot, strike, time_to_expiry, risk_free_rate, volatility, option_type)
print(f"Option price: ${price:.2f}")

# Calculate Greeks
greeks_result = greeks(spot, strike, time_to_expiry, risk_free_rate, volatility, option_type)
print(f"Delta: {greeks_result.delta:.4f}")
print(f"Gamma: {greeks_result.gamma:.4f}")
print(f"Theta: {greeks_result.theta:.4f}")
print(f"Vega: {greeks_result.vega:.4f}")