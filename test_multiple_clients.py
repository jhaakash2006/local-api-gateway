import concurrent.futures

from rate_limiter.sliding_window import SlidingWindowRateLimiter


limiter = SlidingWindowRateLimiter(
    limit=2,
    window_seconds=5
)


def run_client(client_id):
    results = []

    for _ in range(3):
        results.append(
            limiter.is_allowed(client_id)
        )

    return client_id, results


client_ids = [
    "client-1",
    "client-2",
    "client-3",
    "client-4",
    "client-5"
]


def main():
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        results = list(
            executor.map(run_client, client_ids)
        )

    for client_id, client_results in results:
        print(client_id, client_results)


if __name__ == "__main__":
    main()