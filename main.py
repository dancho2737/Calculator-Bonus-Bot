import os
import math
import asyncio
from flask import Flask, request, abort
from telegram import Update, Bot, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# --- Хранилища данных пользователей ---
user_choice_data = {}
user_active_status = {}
user_spam_status = {}
user_count_calc = {}

# --- Клавиатура ---
reply_keyboard = [['Крипто/Бай бонус 20'], ['Депозит бонус 10'], ['Кэшбэк']]
markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)

def format_number(n):
    n_ceil = math.ceil(n)
    s = f"{n_ceil:,}"
    return s.replace(",", " ")

# --- Обработчики команд и сообщений ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_active_status[user_id] = True
    user_spam_status[user_id] = True
    user_count_calc[user_id] = 0
    await update.message.reply_text(
        "Бот активирован. Выбери бонус или расчёт кэшбэка, затем введи сумму:",
        reply_markup=markup
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_active = user_active_status.get(user_id, True)
    if is_active:
        await update.message.reply_text("Бот сейчас активен.")
    else:
        await update.message.reply_text("Бот сейчас остановлен. Напиши /start чтобы включить.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip().lower()

    if not user_active_status.get(user_id, True):
        return

    if text == "stop":
        user_active_status[user_id] = False
        await update.message.reply_text("Бот остановлен. Чтобы запустить снова, напиши /start.")
        return

    if text == "stopspam":
        user_spam_status[user_id] = False
        await update.message.reply_text("Предупреждения больше показываться не будут, кроме каждых 10 подсчётов.")
        return

    if text in ['крипто/бай бонус 20', 'депозит бонус 10', 'кэшбэк']:
        user_choice_data[user_id] = text
        await update.message.reply_text(f"Выбран: {text}. Теперь введи сумму.")
        return

    if user_id in user_choice_data:
        choice = user_choice_data[user_id]
        try:
            sums = float(text.replace(',', '.'))
        except ValueError:
            await update.message.reply_text("Пожалуйста, введи корректное число.")
            return

        if choice == 'депозит бонус 10':
            sums2 = sums * 0.10
            sums3 = sums2 * 15
            slots = sums3 + sums
            roulette = sums3 * 3.33 + sums
            blackjack = sums3 * 5 + sums
            crash = sums3 * 10 + sums

            result = (
                f"Для выполнения условий отыгрыша с вашей суммой бонуса потребуется сделать следующие объёмы ставок:\n\n"
                f"🔹 Слоты (100%) — отыграть {format_number(slots)} сомов\n"
                f"🔹 Roulette (30%) — отыграть {format_number(roulette)} сомов\n"
                f"🔹 Blackjack (20%) — отыграть {format_number(blackjack)} сомов\n"
                f"🔹 Остальные игры (10%) — отыграть {format_number(crash)} сомов"
            )
            await update.message.reply_text(result)

        elif choice == 'крипто/бай бонус 20':
            sums2 = sums * 0.20
            sums3 = sums2 * 20
            slots = sums3 + sums
            roulette = sums3 * 3.33 + sums
            blackjack = sums3 * 5 + sums
            crash = sums3 * 10 + sums

            result = (
                f"Для выполнения условий отыгрыша с вашей суммой бонуса потребуется сделать следующие объёмы ставок:\n\n"
                f"🔹 Слоты (100%) — отыграть {format_number(slots)} сомов\n"
                f"🔹 Roulette (30%) — отыграть {format_number(roulette)} сомов\n"
                f"🔹 Blackjack (20%) — отыграть {format_number(blackjack)} сомов\n"
                f"🔹 Остальные игры (10%) — отыграть {format_number(crash)} сомов"
            )
            await update.message.reply_text(result)

        elif choice == 'кэшбэк':
            if sums < 500:
                await update.message.reply_text("Для кэшбэка нужно минимум 500 сом чистых потерь.")
                return

            if 500 <= sums < 5000:
                percent = 10
            elif 5000 <= sums < 30000:
                percent = 15
            else:
                percent = 20

            cashback = sums * percent / 100
            await update.message.reply_text(
                f"Для кэшбэка нужно минимум 500 сом чистых потерь за 24 часа.\n"
                f"Чистые потери = депозиты − выводы.\n\n"
                f"Например: {format_number(sums)} − 1 000 = {format_number(sums - 1000)} сом\n\n"
                f"Размер кэшбэка:\n"
                f"500–4 999 сом — 10%,\n"
                f"5 000–29 999 сом — 15%,\n"
                f"от 30 000 — 20%\n\n"
                f"{format_number(sums)} сом × {percent}% = {format_number(cashback)} сом кэшбэка."
            )
            return

        user_count_calc[user_id] = user_count_calc.get(user_id, 0) + 1
        count = user_count_calc[user_id]

        if choice != 'кэшбэк':
            if user_spam_status.get(user_id, True):
                await update.message.reply_text(
                    "Обязательно перепроверяйте итоговые суммы! Это для вашей страховки.\n"
                    "Чтобы отключить это сообщение — напишите stopspam"
                )
            elif count % 10 == 0:
                await update.message.reply_text(
                    "Напоминание: перепроверьте итоговые суммы ставок!"
                )
    else:
        await update.message.reply_text("Сначала выбери бонус или кэшбэк кнопкой ниже.", reply_markup=markup)

# --- Flask + Webhook ---
app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable not set")

bot = Bot(token=BOT_TOKEN)
application = ApplicationBuilder().token(BOT_TOKEN).build()

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("status", status))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def webhook():
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), bot)
        asyncio.run(application.process_update(update))
        return "OK"
    else:
        abort(405)

@app.route("/")
def home():
    return "Bot is alive!"

async def set_webhook():
    if not WEBHOOK_URL:
        print("WEBHOOK_URL not set.")
        return
    await bot.set_webhook(f"{WEBHOOK_URL}/webhook/{BOT_TOKEN}")

if __name__ == "__main__":
    asyncio.run(set_webhook())
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
