from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from flask import Flask, request
import os
import math
import asyncio
import threading

# Хранилища состояния пользователей
user_choice_data = {}
user_active_status = {}
user_spam_status = {}     # True — показывать полное предупреждение, False — выключил (только короткое каждые 10 подсчётов)
user_count_calc = {}      # Счётчик подсчётов для каждого пользователя

# Клавиатура с вариантами
reply_keyboard = [['Крипто/Бай бонус 20'], ['Депозит бонус 10'], ['Кэшбэк']]
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
                "Для выполнения условий отыгрыша с вашей суммой бонуса потребуется сделать следующие объёмы ставок в разных играх:\n\n"
                f"🔹 Слоты (100%) — отыграть {format_number(slots)} сомов\n"
                f"🔹 Roulette (30%) — отыграть {format_number(roulette)} сомов\n"
                f"🔹 Blackjack (20%) — отыграть {format_number(blackjack)} сомов\n"
                f"🔹 Остальные настольные, crash игры и лайв-казино игры (10%) — отыграть {format_number(crash)} сомов"
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
                "Для выполнения условий отыгрыша с вашей суммой бонуса потребуется сделать следующие объёмы ставок в разных играх:\n\n"
                f"🔹 Слоты (100%) — отыграть {format_number(slots)} сомов\n"
                f"🔹 Roulette (30%) — отыграть {format_number(roulette)} сомов\n"
                f"🔹 Blackjack (20%) — отыграть {format_number(blackjack)} сомов\n"
                f"🔹 Остальные настольные, crash игры и лайв-казино игры (10%) — отыграть {format_number(crash)} сомов"
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
                "Для кэшбэка нужно минимум 500 сом чистых потерь за 24 часа. "
                "Чистые потери считаются так:\n"
                "депозиты без бонусов − выводы = чистые потери.\n\n"
                f"Например, вы внесли и проиграли {format_number(sums)} сом, но до этого вывели 1 000 сом. "
                "«Этот вывод мог быть с прошлого депозита или бонуса». Тогда чистые потери = "
                f"{format_number(sums)} − 1 000 = {format_number(sums - 1000)} сом.\n\n"
                "Размер кэшбэка зависит от суммы потерь:\n"
                "От 500 до 4 999 сом — 10%,\n"
                "от 5 000 до 29 999 сом — 15%,\n"
                "от 30 000 и выше — 20%.\n\n"
                f"В вашем случае {format_number(sums)} сом × {percent}% = {format_number(cashback)} сом кэшбэка.\n"
                "Если нужно — помогу посчитать другие суммы!"
            )
            return

        # Счётчик подсчётов (не для кэшбэка)
        user_count_calc[user_id] = user_count_calc.get(user_id, 0) + 1
        count = user_count_calc[user_id]

        if choice != 'кэшбэк':
            if user_spam_status.get(user_id, True):
                await update.message.reply_text(
                    "Обязательно перепроверяйте итоговые суммы! Это для вашей же страховки. "
                    "Если же хотите чтобы это сообщение больше не появлялось, то напишите stopspam"
                )
            else:
                if count % 10 == 0:
                    await update.message.reply_text(
                        "Обязательно перепроверяйте итоговые суммы! Это для вашей же страховки."
                    )

    else:
        await update.message.reply_text("Сначала выбери бонус или кэшбэк кнопкой ниже.", reply_markup=markup)

# --- Flask app для пинга Render ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running."

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# --- Запуск Telegram бота и Flask в потоках ---
async def run_bot():
    app_telegram = ApplicationBuilder().token(os.environ.get("BOT_TOKEN")).build()
    app_telegram.add_handler(CommandHandler('start', start))
    app_telegram.add_handler(CommandHandler('status', status))
    app_telegram.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    await app_telegram.run_polling()

def main():
    # Запуск Flask сервера в отдельном потоке
    threading.Thread(target=run_flask).start()
    # Запуск Telegram бота в асинхронном цикле
    asyncio.run(run_bot())

if __name__ == '__main__':
    main()
