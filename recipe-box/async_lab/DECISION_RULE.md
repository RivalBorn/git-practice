# Decision rule

- Keep code synchronous when the work is simple or CPU-bound, or when there is no need to overlap waiting.
- Use threads when existing synchronous code spends time waiting on I/O and you want to overlap that work without rewriting it for async.
- Use async with `asyncio.gather` for multiple independent I/O operations when the client libraries support async. Start the operations together and await them as a group; awaiting each request one by one still makes them sequential.
