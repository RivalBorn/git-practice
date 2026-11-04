import asyncio
import time

import httpx


async def main():
    async with httpx.AsyncClient() as client:
        start_time = time.perf_counter()
        for _ in range(3):
            response = await client.get("http://127.0.0.1:5001/eggs")
            response.raise_for_status()
        end_time = time.perf_counter()

    print(f"Total time: {end_time - start_time:.2f} seconds")


if __name__ == "__main__":
    asyncio.run(main())
