import json
import os
import datetime
import random
import time
import asyncio
import pytz
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler

# --- КОНФИГУРАЦИЯ (проверьте свои данные) ---
BOT_TOKEN = "8491189136:AAEOH-8Rt0GQv5R76ToE_coQlHQlxecPHHM"
ADMIN_ID = 5928505508
TZ = pytz.timezone('Asia/Krasnoyarsk')
DATA_FILE = "slots_data.json"

# --- ФУНКЦИИ РАБОТЫ С ДАННЫМИ ---
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"slots": {}, "days_off": [], "pending": {}}
    with open(DATA_FILE, 'r') as f:
        data = json.load(f)
        data["days_off"] = data.get("days_off", [])
        data["pending"] = data.get("pending", {})
        return data

def save_data(data):
    to_save = {"slots": data["slots"], "days_off": data["days_off"], "pending": data["pending"]}
    with open(DATA_FILE, 'w') as f:
        json.dump(to_save, f)

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER (ОБЯЗАТЕЛЬНО!) ---
async def health_check(request):
    return web.Response(text="OK")

async def run_web_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"✅ Веб-сервер для health checks запущен на порту {port}")
    while True:
        await asyncio.sleep(3600)

# --- ВСЕ ВАШИ ОБРАБОТЧИКИ КОМАНД ---
# (Скопируйте сюда все ваши функции: start, show_free_slots, date_callback,
#  time_callback, get_name, get_phone, get_vk, get_tg, shoot_type_callback,
#  agreements_callback, confirm_request, decline_request, admin_callback,
#  add_slot, free_slot, day_off, day_on, show_slots)

# --- УПРОЩЁННЫЙ /start (без Markdown, чтобы не было ошибок) ---
async def start(update, context):
    await update.message.reply_text(
        "📸 Фотограф «В моменте»\nКрасноярск / Новосибирск\n\n"
        "Напиши /slots_free, чтобы посмотреть свободные слоты.\n\n"
        "Команды админа:\n/add_slot 2025-05-20 17:00\n/day_off 2025-05-20\n/slots"
    )

# --- ОСНОВНАЯ ФУНКЦИЯ ---
def main():
    # Запускаем веб-сервер для Render
    loop = asyncio.get_event_loop()
    loop.create_task(run_web_server())

    # Создаём приложение бота
    application = Application.builder().token(BOT_TOKEN).build()

    # Регистрируем обработчики команд (укажите все, что есть в вашем боте)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("slots_free", show_free_slots))
    application.add_handler(CommandHandler("add_slot", add_slot))
    application.add_handler(CommandHandler("free", free_slot))
    application.add_handler(CommandHandler("day_off", day_off))
    application.add_handler(CommandHandler("day_on", day_on))
    application.add_handler(CommandHandler("slots", show_slots))
    application.add_handler(CallbackQueryHandler(date_callback, pattern="^date_"))
    application.add_handler(CallbackQueryHandler(admin_callback, pattern="^(confirm_|decline_)"))

    # ConversationHandler (скопируйте ваш, но без лишних предупреждений)
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(time_callback, pattern="^time_")],
        states={
            "GET_NAME": [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            "GET_PHONE": [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            "GET_VK": [MessageHandler(filters.TEXT & ~filters.COMMAND, get_vk)],
            "GET_TG": [MessageHandler(filters.TEXT & ~filters.COMMAND, get_tg)],
            "GET_SHOOT_TYPE": [CallbackQueryHandler(shoot_type_callback)],
            "GET_AGREEMENTS": [CallbackQueryHandler(agreements_callback)],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: u.message.reply_text("❌ Отмена"))],
    )
    application.add_handler(conv)

    print("🤖 Бот запущен и готов к работе!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
