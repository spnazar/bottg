import aiohttp
import asyncio

TOKEN = "https://l.kaspi.kz/shop/8q7QRK9zRRNzFpf"

async def test():
    headers = {"Authorization": f"Bearer {TOKEN}"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://kaspi.kz/shop/api/v2/orders/",
                headers=headers,
                params={"page[number]": 0, "page[size]": 1},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                print(f"Статус: {resp.status}")
                text = await resp.text()
                print(f"Ответ: {text[:300]}")
    except Exception as e:
        print(f"Ошибка: {type(e).__name__}: {e}")

asyncio.run(test())