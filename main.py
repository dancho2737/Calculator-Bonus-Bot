from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import os
import math
import asyncio

TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

user_choice_data = {}
user_active_status = {}
user_spam_status = {}
user_count_calc = {}

reply_keyboard = [['Крипто/Бай бонус 20'], ['Депозит бонус 10']]
markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)

def format_number(n):
    n_ceil = math.ceil(n)
    s = f"{n_ceil:,}"
    return s.replace(",", " ")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_active_status[user_id] = True
    user_spam_status[user_id] = True
    user_count_calc[user_id] = 0
    await update.message.reply_text(
        "Бот активирован. Выбери бонус для расчёта и введи сумму:",
        reply_markup=markup
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_active = user_active_status.get(user_id, True)
    msg = "Бот сейчас активен." if is_active else "Бот сейчас остановлен. Напиши /start чтобы включить."
    await update.message.reply_text(msg)

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

    if text in ['крипто/бай бонус 20', 'депозит бонус 10']:
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
        elif choice == 'крипто/бай бонус 20':
            sums2 = sums * 0.20
            sums3 = sums2 * 20
        else:
            await update.message.reply_text("Ошибка выбора бонуса.")
            return

        slots = sums3 + sums
        roulette = sums3 * 3.33 + sums
        blackjack = sums3 * 5 + sums
        crash = sums3 * 10 + sums

        result = (
            f"Для выполнения условий отыгрыша с вашей суммой бонуса потребуется сделать следующие объёмы ставок:\n\n"
            f"🔹 Слоты (100%) — отыграть {format_number(slots)} сомов\n"
            f"🔹 Roulette (30%) — отыграть {format_number(roulette)} сомов\n"
            f"🔹 Blackjack (20%) — отыграть {format_number(blackjack)} сомов\n"
            f"🔹 Остальные настольные, crash и лайв-казино (10%) — отыграть {format_number(crash)} сомов"
        )

        await update.message.reply_text(result)

        user_count_calc[user_id] = user_count_calc.get(user_id, 0) + 1
        count = user_count_calc[user_id]

        if user_spam_status.get(user_id, True):
            await update.message.reply_text(
                "Обязательно перепроверяйте итоговые суммы! Это для вашей же страховки. "
                "Если хотите отключить эти сообщения — напишите stopspam"
            )
        elif count % 10 == 0:
            await update.message.reply_text(
                "Обязательно перепроверяйте итоговые суммы! Это для вашей же страховки."
            )
    else:
        await update.message.reply_text("Сначала выбери бонус кнопкой ниже.", reply_markup=markup)

flask_app = Flask(__name__)

application = Application.builder().token(TOKEN).build()

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("status", status))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

@flask_app.post("/")
async def webhook() -> str:
    update = Update.de_json(await request.get_json(force=True), application.bot)
    await application.update_queue.put(update)
    return "ok"

@flask_app.get("/")
def index():
    return "Бот запущен и работает"

async def main():
    await application.bot.set_webhook(WEBHOOK_URL)
    await application.initialize()
    await application.start()
    print("Бот запущен (WebHook)")
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
