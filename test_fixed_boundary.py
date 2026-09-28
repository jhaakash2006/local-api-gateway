import time

from rate_limiter.fixed_window import FixedWindowRateLimiter


limiter = FixedWindowRateLimiter(
    limit=2,
    window_seconds=5
)


print("Request 1:", limiter.is_allowed("client-1"))
print("Request 2:", limiter.is_allowed("client-1"))
print("Request 3:", limiter.is_allowed("client-1"))

print("Waiting for the next fixed window...")
time.sleep(5.1)

print("Request 4 after window:", limiter.is_allowed("client-1"))
print("Request 5 after window:", limiter.is_allowed("client-1"))
print("Request 6 after window:", limiter.is_allowed("client-1"))