import requests

TOKEN = ""

resp = requests.get(
    "https://kaspi.kz/shop/api/v2/orders/",
    headers={
        "X-Auth-Token": TOKEN,
        "Accept": "application/json",
        "Content-Type": "application/vnd.api+json",
    },
    params={"page[number]": 0, "page[size]": 1},
    timeout=30,
)
print(f"Статус: {resp.status_code}")

print(f"Ответ: {resp.text[:500]}")
