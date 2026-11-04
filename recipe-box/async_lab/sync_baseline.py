import threading
import time

import httpx


def fetch_one():
    response = httpx.get("http://127.0.0.1:5001/nutrition/eggs")
    response.raise_for_status()
    print(response.status_code)


def count_up():
    total = 0
    for i in range(50_000_000):
        total += 1


total_start = time.perf_counter()

start_time = time.perf_counter()
response = httpx.get("http://127.0.0.1:5001/nutrition/eggs")
end_time = time.perf_counter()

response.raise_for_status()
print(response.json())
print(f"Elapsed time: {end_time - start_time:.2f} seconds")

start_time = time.perf_counter()
response = httpx.get("http://127.0.0.1:5001/nutrition/eggs")
end_time = time.perf_counter()

response.raise_for_status()
print(f"Elapsed time: {end_time - start_time:.2f} seconds")

start_time = time.perf_counter()
response = httpx.get("http://127.0.0.1:5001/nutrition/eggs")
end_time = time.perf_counter()

response.raise_for_status()
print(f"Elapsed time: {end_time - start_time:.2f} seconds")

total_end = time.perf_counter()
print("total:", total_end - total_start)

threads = [threading.Thread(target=fetch_one) for _ in range(3)]
threaded_start = time.perf_counter()

for thread in threads:
    thread.start()

for thread in threads:
    thread.join()

threaded_end = time.perf_counter()
print("threaded total:", threaded_end - threaded_start)

cpu_start = time.time()
count_up()
cpu_end = time.time()
print("cpu sequential:", cpu_end - cpu_start)

threads = []
for _ in range(4):
    threads.append(threading.Thread(target=count_up))

cpu_threaded_start = time.time()
for thread in threads:
    thread.start()

for thread in threads:
    thread.join()

cpu_threaded_end = time.time()
print("cpu threaded:", cpu_threaded_end - cpu_threaded_start)
