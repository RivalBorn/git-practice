# Async HTTP timings

- Sequential async requests (3 calls to `/eggs`): 3.04 seconds
- Concurrent async requests with `asyncio.gather` (3 calls to `/eggs`): 1.04 seconds
