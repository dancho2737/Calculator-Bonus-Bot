from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import os
import math

user_choice_data = {}
user_active_status = {}
user_spam_status = {}     # True — показывать полное предупреждение, False — выключил (только короткое каждые 10 подсчётов)
user_count_calc = {}      # Счётчик подсчётов для каждого пользователя

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
                f"Для выполнения условий отыгрыша с вашей суммой бонуса потребуется сделать следующие объёмы ставок в разных играх:\n\n"
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
                f"Для выполнения условий отыгрыша с вашей суммой бонуса потребуется сделать следующие объёмы ставок в разных играх:\n\n"
                f"🔹 Слоты (100%) — отыграть {format_number(slots)} сомов\n"
                f"🔹 Roulette (30%) — отыграть {format_number(roulette)} сомов\n"
                f"🔹 Blackjack (20%) — отыграть {format_number(blackjack)} сомов\n"
                f"🔹 Остальные настольные, crash игры и лайв-казино игры (10%) — отыграть {format_number(crash)} сомов"
            )
            await update.message.reply_text(result)

        elif choice == 'кэшбэк':
