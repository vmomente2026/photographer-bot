import json
import os
import datetime
import random
import time
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler

BOT_TOKEN = "8491189136:AAEOH-8Rt0GQv5R76ToE_coQlHQlxecPHHM"
ADMIN_ID = 5928505508
TZ = pytz.timezone('Asia/Krasnoyarsk')
DATA_FILE = "slots_data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "slots": {},
            "days_off": [],
            "pending": {}
        }
    with open(DATA_FILE, 'r') as f:
        data = json.load(f)
        data["days_off"] = data.get("days_off", [])
        data["pending"] = data.get("pending", {})
        return data

def save_data(data):
    to_save = {
        "slots": data["slots"],
        "days_off": data["days_off"],
        "pending": data["pending"]
    }
    with open(DATA_FILE, 'w') as f:
        json.dump(to_save, f)

async def start(update, context):
    await update.message.reply_text(
        "📸 *Фотограф «В моменте»*\nКрасноярск / Новосибирск\n\n"
        "Напиши /slots_free, чтобы посмотреть свободные слоты.\n\n"
        "*Команды админа:*\n/add_slot 2025-05-20 17:00\n/day_off 2025-05-20\n/slots",
        parse_mode="Markdown"
    )

async def show_free_slots(update, context):
    today = datetime.datetime.now(TZ).date()
    data = load_data()
    free_by_day = {}
    for i in range(14):
        date = today + datetime.timedelta(days=i)
        date_str = date.isoformat()
        if date_str in data["days_off"]:
            continue
        for slot, status in data["slots"].items():
            if slot.startswith(date_str) and status == "free":
                time_slot = slot.split()[1]
                if date_str not in free_by_day:
                    free_by_day[date_str] = []
                free_by_day[date_str].append(time_slot)
    if not free_by_day:
        await update.message.reply_text("😞 На ближайшие дни нет свободных слотов.")
        return
    keyboard = []
    for date_str in free_by_day:
        day = datetime.datetime.strptime(date_str, "%Y-%m-%d").day
        month = datetime.datetime.strptime(date_str, "%Y-%m-%d").month
        keyboard.append([InlineKeyboardButton(f"📅 {day}.{month}", callback_data=f"date_{date_str}")])
    await update.message.reply_text("🗓 *Выбери дату:*", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def date_callback(update, context):
    query = update.callback_query
    await query.answer()
    date_str = query.data.replace("date_", "")
    data = load_data()
    free_times = []
    for slot, status in data["slots"].items():
        if slot.startswith(date_str) and status == "free":
            free_times.append(slot.split()[1])
    if not free_times:
        await query.edit_message_text("😞 На эту дату нет свободных слотов.")
        return
    keyboard = [[InlineKeyboardButton(f"🕒 {t}", callback_data=f"time_{date_str}_{t}")] for t in sorted(free_times)]
    await query.edit_message_text(f"🗓 *{date_str}*\nВыбери время:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    context.user_data['selected_date'] = date_str

async def time_callback(update, context):
    query = update.callback_query
    await query.answer()
    parts = query.data.split("_")
    date_str = parts[1]
    time_slot = parts[2]
    context.user_data['selected_slot'] = f"{date_str} {time_slot}"
    await query.edit_message_text("📝 *Напиши своё имя и фамилию:*", parse_mode="Markdown")
    return "GET_NAME"

async def get_name(update, context):
    context.user_data['name'] = update.message.text
    await update.message.reply_text("📞 *Номер телефона:*", parse_mode="Markdown")
    return "GET_PHONE"

async def get_phone(update, context):
    context.user_data['phone'] = update.message.text
    await update.message.reply_text("🔗 *Ссылка на VK (можно пропустить):*", parse_mode="Markdown")
    return "GET_VK"

async def get_vk(update, context):
    context.user_data['vk'] = update.message.text if update.message.text else "—"
    await update.message.reply_text("📱 *Ссылка на Telegram (можно пропустить):*", parse_mode="Markdown")
    return "GET_TG"

async def get_tg(update, context):
    context.user_data['tg'] = update.message.text if update.message.text else "—"
    keyboard = [
        [InlineKeyboardButton("🏙 Уличная", callback_data="Уличная")],
        [InlineKeyboardButton("🎨 Творческая", callback_data="Творческая")],
        [InlineKeyboardButton("💍 Свадебная", callback_data="Свадебная")],
        [InlineKeyboardButton("📰 Репортажная", callback_data="Репортажная")],
        [InlineKeyboardButton("📊 Реклама/Коммерция", callback_data="Реклама/Коммерция")],
        [InlineKeyboardButton("🔄 TFP", callback_data="TFP")]
    ]
    await update.message.reply_text("🎬 *Тип съёмки:*", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return "GET_SHOOT_TYPE"

async def shoot_type_callback(update, context):
    query = update.callback_query
    await query.answer()
    context.user_data['shoot_type'] = query.data
    keyboard = [
        [InlineKeyboardButton("✅ Согласен на обработку ПД", callback_data="pd_yes")],
        [InlineKeyboardButton("✅ Ознакомлен с правилами", callback_data="rules_yes")]
    ]
    if query.data == "TFP":
        keyboard.append([InlineKeyboardButton("📜 Согласен с TFP", callback_data="tfp_yes")])
    await query.edit_message_text("🔐 *Подтверди согласие:*", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return "GET_AGREEMENTS"

async def agreements_callback(update, context):
    query = update.callback_query
    await query.answer()
    context.user_data.setdefault('agreements', []).append(query.data)
    required = ['pd_yes', 'rules_yes']
    if context.user_data['shoot_type'] == "TFP":
        required.append('tfp_yes')
    if all(r in context.user_data['agreements'] for r in required):
        slot = context.user_data['selected_slot']
        data = load_data()
        if slot in data["slots"] and data["slots"][slot] == "free":
            request_id = str(int(time.time())) + str(random.randint(10, 99))
            data["pending"][request_id] = {
                "slot": slot,
                "chat_id": update.effective_chat.id,
                "client": {
                    "name": context.user_data['name'],
                    "phone": context.user_data['phone'],
                    "vk": context.user_data['vk'],
                    "tg": context.user_data['tg'],
                    "shoot_type": context.user_data['shoot_type']
                }
            }
            data["slots"][slot] = f"pending:{request_id}"
            save_data(data)
            keyboard = [
                [InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm_{request_id}")],
                [InlineKeyboardButton("❌ Отклонить", callback_data=f"decline_{request_id}")]
            ]
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"📸 *НОВАЯ ЗАЯВКА*\n\n👤 {context.user_data['name']}\n📞 {context.user_data['phone']}\n🎬 {context.user_data['shoot_type']}\n📅 {slot}",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
            await query.edit_message_text(f"⏳ *Заявка отправлена!*\n\n📅 {slot}\nФотограф свяжется с вами для подтверждения.", parse_mode="Markdown")
        else:
            await query.edit_message_text("❌ Слот уже занят. Попробуй /slots_free")
        return ConversationHandler.END
    else:
        await query.edit_message_text("✅ Подтверди остальные согласия.")
        return "GET_AGREEMENTS"

async def confirm_request(update, context, request_id):
    data = load_data()
    if request_id not in data["pending"]:
        await update.callback_query.answer("Заявка не найдена")
        return
    pending = data["pending"][request_id]
    slot = pending["slot"]
    client = pending["client"]
    data["slots"][slot] = f"booked:{client['name']}:{client['phone']}"
    del data["pending"][request_id]
    save_data(data)
    await context.bot.send_message(chat_id=pending["chat_id"], text=f"✅ *Запись на {slot} подтверждена! Жду вас. 📸*", parse_mode="Markdown")
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(f"✅ Заявка {client['name']} на {slot} подтверждена")

async def decline_request(update, context, request_id):
    data = load_data()
    if request_id not in data["pending"]:
        await update.callback_query.answer("Заявка не найдена")
        return
    pending = data["pending"][request_id]
    slot = pending["slot"]
    data["slots"][slot] = "free"
    del data["pending"][request_id]
    save_data(data)
    await context.bot.send_message(chat_id=pending["chat_id"], text=f"❌ *Заявка на {slot} отклонена. Попробуйте другое время: /slots_free*", parse_mode="Markdown")
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(f"❌ Заявка отклонена")

async def admin_callback(update, context):
    query = update.callback_query
    data_cb = query.data
    if data_cb.startswith("confirm_"):
        await confirm_request(update, context, data_cb.replace("confirm_", ""))
    elif data_cb.startswith("decline_"):
        await decline_request(update, context, data_cb.replace("decline_", ""))

async def add_slot(update, context):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        date = context.args[0]
        time_slot = context.args[1]
        slot = f"{date} {time_slot}"
        data = load_data()
        data["slots"][slot] = "free"
        save_data(data)
        await update.message.reply_text(f"✅ Слот {slot} добавлен")
    except:
        await update.message.reply_text("❌ /add_slot 2025-05-20 17:00")

async def free_slot(update, context):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        date = context.args[0]
        time_slot = context.args[1]
        slot = f"{date} {time_slot}"
        data = load_data()
        if slot in data["slots"]:
            data["slots"][slot] = "free"
            save_data(data)
            await update.message.reply_text(f"✅ Слот {slot} освобождён")
    except:
        await update.message.reply_text("❌ /free 2025-05-20 17:00")

async def day_off(update, context):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        date = context.args[0]
        data = load_data()
        if date not in data["days_off"]:
            data["days_off"].append(date)
            save_data(data)
            await update.message.reply_text(f"⛔ {date} выходной")
    except:
        await update.message.reply_text("❌ /day_off 2025-05-20")

async def day_on(update, context):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        date = context.args[0]
        data = load_data()
        if date in data["days_off"]:
            data["days_off"].remove(date)
            save_data(data)
            await update.message.reply_text(f"✅ {date} рабочий")
    except:
        await update.message.reply_text("❌ /day_on 2025-05-20")

async def show_slots(update, context):
    if update.effective_user.id != ADMIN_ID:
        return
    data = load_data()
    booked = [s for s, st in data["slots"].items() if st.startswith("booked")]
    pending = [s for s, st in data["slots"].items() if st.startswith("pending")]
    msg = "📅 *Занятые слоты:*\n" + "\n".join(booked) if booked else "✅ Нет занятых слотов"
    if pending:
        msg += "\n\n⏳ *Ожидают подтверждения:*\n" + "\n".join(pending)
    await update.message.reply_text(msg, parse_mode="Markdown")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
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
        fallbacks=[CommandHandler("cancel", lambda u,c: u.message.reply_text("❌ Отмена"))],
    )
    app.add_handler(conv)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("slots_free", show_free_slots))
    app.add_handler(CallbackQueryHandler(date_callback, pattern="^date_"))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern="^(confirm_|decline_)"))
    app.add_handler(CommandHandler("add_slot", add_slot))
    app.add_handler(CommandHandler("free", free_slot))
    app.add_handler(CommandHandler("day_off", day_off))
    app.add_handler(CommandHandler("day_on", day_on))
    app.add_handler(CommandHandler("slots", show_slots))
    print("🤖 Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
