import asyncio
import time

import httpx


async def main():
    async with httpx.AsyncClient() as client:
        start_time = time.perf_counter()
        tasks = [
            client.get("http://127.0.0.1:5001/eggs"),
            client.get("http://127.0.0.1:5001/eggs"),
            client.get("http://127.0.0.1:5001/eggs"),
        ]
        responses = await asyncio.gather(*tasks)
        for response in responses:
            response.raise_for_status()
        end_time = time.perf_counter()

    print(f"Total time: {end_time - start_time:.2f} seconds")


if __name__ == "__main__":
    asyncio.run(main())
