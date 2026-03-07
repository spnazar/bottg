import os

BOT_TOKEN = os.environ.get("BOT_TOKEN")

# Переключи на False когда получишь токен от сестры
DEMO_MODE = False

# Как часто проверять (в минутах)
CHECK_ORDERS_INTERVAL = 2    # Заказы — каждые 2 минуты
CHECK_PRICES_INTERVAL  = 30  # Цены конкурентов — каждые 30 минут
CHECK_STOCK_INTERVAL   = 60  # Остатки — каждый час

# Предупреждение если осталось меньше N штук
LOW_STOCK_THRESHOLD = 5

# Твой Telegram для поддержки
SUPPORT_USERNAME = "@yo"
