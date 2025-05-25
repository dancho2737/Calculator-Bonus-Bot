from flask import Flask, request, abort
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import os
import math
import asyncio

TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")  # Например https://yourapp.onrender.com

# Состояния пользователей
user_choice_data = {}
user_active_status = {}

reply_keyboard = [['Крипто/Бай бонус 20'], ['Депозит бонус 10']]
markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)

def format_number(n):
    n_ceil = math.ceil(n)
    s = f"{n_ceil:,}"
    return s.replace(",", " ")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_active_status[user_id] = True
    await update.message.reply_text(
        "Бот активирован. Выбери бонус для расчёта и введи сумму:",
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
    else:
        await update.message.reply_text("Сначала выбери бонус кнопкой ниже.", reply_markup=markup)


# Flask-приложение
flask_app = Flask(__name__)

# Создаём telegram application
application = Application.builder().token(TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("status", status))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))


@flask_app.route('/', methods=["POST"])
def webhook():
    # Принимаем update от Telegram
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), application.bot)
        # Обрабатываем update в отдельной таске asyncio
        asyncio.create_task(application.update_queue.put(update))
        return "ok"
    else:
        abort(405)


async def main():
    # Устанавливаем webhook
    await application.bot.set_webhook(WEBHOOK_URL)
    await application.initialize()
    await application.start()
    print("Бот запущен (WebHook)")
    # Запускаем Flask сервер на 0.0.0.0:PORT
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))


if __name__ == '__main__':
    asyncio.run(main())
