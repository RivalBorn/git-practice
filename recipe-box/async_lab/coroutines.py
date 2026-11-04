import asyncio


async def inner():
    print("inner: start")
    await asyncio.sleep(1)
    print("inner: end")
    return 10


async def outer():
    print("outer: before inner")
    value = await inner()
    print("outer: after inner, value =", value)


asyncio.run(outer())
