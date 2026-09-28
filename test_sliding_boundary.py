import time

from rate_limiter.sliding_window import SlidingWindowRateLimiter


limiter = SlidingWindowRateLimiter(
    limit=2,
    window_seconds=5
)


print("Request 1:", limiter.is_allowed("client-1"))
print("Request 2:", limiter.is_allowed("client-1"))
print("Request 3:", limiter.is_allowed("client-1"))

print("Waiting for the sliding window to expire...")
time.sleep(5.1)

print("Request 4 after window:", limiter.is_allowed("client-1"))