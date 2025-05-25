from flask import Flask
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import os
import math
import threading

# Переменные
TOKEN = os.environ.get("BOT_TOKEN")
PORT = int(os.environ.get("PORT", 5000))

user_choice_data = {}
user_active_status = {}
user_spam_status = {}
user_count_calc = {}

reply_keyboard = [['Крипто/Бай бонус 20'], ['Депозит бонус 10']]
markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)

# Функции
def format_number(n):
    n_ceil = math.ceil(n)
    s = f"{n_ceil:,}"
    return s.replace(",", " ")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_active_status[user_id] = True
    user_spam_status[user_id] = True
    user_count_calc[user_id] = 0
    await update.message.reply_text("Бот активирован. Выбери бонус и введи сумму:", reply_markup=markup)

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
        await update.message.reply_text("Бот остановлен. Напиши /start чтобы снова включить.")
        return

    if text == "stopspam":
        user_spam_status[user_id] = False
        await update.message.reply_text("Предупреждения отключены (только каждые 10 подсчётов).")
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
            await update.message.reply_text("Введи корректное число.")
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
            f"Для выполнения условий отыгрыша с бонусом нужно сделать:\n\n"
            f"🔹 Слоты (100%) — отыграть {format_number(slots)} сомов\n"
            f"🔹 Roulette (30%) — отыграть {format_number(roulette)} сомов\n"
            f"🔹 Blackjack (20%) — отыграть {format_number(blackjack)} сомов\n"
            f"🔹 Остальные игры, Crash и лайв-казино (10%) — отыграть {format_number(crash)} сомов"
        )

        await update.message.reply_text(result)

        user_count_calc[user_id] = user_count_calc.get(user_id, 0) + 1
        count = user_count_calc[user_id]

        if user_spam_status.get(user_id, True):
            await update.message.reply_text(
                "Обязательно перепроверяйте итоговые суммы! Это для вашей страховки. "
                "Чтобы отключить это сообщение, напишите stopspam"
            )
        elif count % 10 == 0:
            await update.message.reply_text("Обязательно перепроверяйте итоговые суммы!")
    else:
        await update.message.reply_text("Сначала выбери бонус кнопкой ниже.", reply_markup=markup)

# Telegram bot запускается в отдельном потоке
def run_bot():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

# Flask только чтобы Render "видел" порт
flask_app = Flask(__name__)

@flask_app.route('/')
def index():
    return "Бот работает! 🎉"

if __name__ == '__main__':
    threading.Thread(target=run_bot).start()
    flask_app.run(host="0.0.0.0", port=PORT)
