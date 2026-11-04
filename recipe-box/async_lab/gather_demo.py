import asyncio


async def wait_and_return(seconds):
    await asyncio.sleep(seconds)
    return seconds


async def main():
    task1 = asyncio.create_task(wait_and_return(1))
    task2 = asyncio.create_task(wait_and_return(2))
    task3 = asyncio.create_task(wait_and_return(3))
    results = await asyncio.gather(task1, task2, task3)
    print(results)


if __name__ == "__main__":
    asyncio.run(main())
