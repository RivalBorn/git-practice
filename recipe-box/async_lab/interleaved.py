import asyncio


async def task_a():
    for i in range(1, 4):
        await asyncio.sleep(1)
        print(f"A{i}")


async def task_b():
    for i in range(1, 4):
        await asyncio.sleep(1)
        print(f"B{i}")


async def main():
    await asyncio.gather(task_a(), task_b())


if __name__ == "__main__":
    asyncio.run(main())
