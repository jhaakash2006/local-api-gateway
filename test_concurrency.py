import concurrent.futures
import requests


URL = "http://127.0.0.1:8000/api/users/users"


def send_request():
    try:
        response = requests.get(URL)
        return response.status_code
    except requests.RequestException:
        return None


with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    results = list(
        executor.map(
            lambda _: send_request(),
            range(10)
        )
    )


print("Results:", results)
print("200:", results.count(200))
print("429:", results.count(429))