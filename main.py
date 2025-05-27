from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import os
import math

user_choice_data = {}
user_active_status = {}
user_spam_status = {}
user_count_calc = {}
user_authenticated = {}  # Пользователи, прошедшие проверку пароля

PASSWORD = "starzbetbot"

reply_keyboard = [['Крипто/Бай бонус 20'], ['Депозит бонус 10']]
markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)

def format_number(n):
    n_ceil = math.ceil(n)
    return f"{n_ceil:,}".replace(",", " ")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not user_authenticated.get(user_id):
        await update.message.reply_text("Введите пароль для доступа к боту:")
        return

    user_active_status[user_id] = True
    user_spam_status[user_id] = True
    user_count_calc[user_id] = 0
    await update.message.reply_text(
        "Бот активирован. Выбери бонус для расчёта и введи сумму:",
        reply_markup=markup
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not user_authenticated.get(user_id):
        await update.message.reply_text("Сначала введите пароль. Напиши /start.")
        return

    is_active = user_active_status.get(user_id, True)
    await update.message.reply_text("Бот сейчас активен." if is_active else "Бот сейчас остановлен. Напиши /start чтобы включить.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if not user_authenticated.get(user_id):
        if text == PASSWORD:
            user_authenticated[user_id] = True
            user_active_status[user_id] = True
            user_spam_status[user_id] = True
            user_count_calc[user_id] = 0
            await update.message.reply_text("Доступ разрешён! Выбери бонус и введи сумму:", reply_markup=markup)
        else:
            await update.message.reply_text("Неверный пароль. Повторите попытку.")
        return

    if not user_active_status.get(user_id, True):
        return

    if text.lower() == "stop":
        user_active_status[user_id] = False
        await update.message.reply_text("Бот остановлен. Чтобы запустить снова, напиши /start.")
        return

    if text.lower() == "stopspam":
        user_spam_status[user_id] = False
        await update.message.reply_text("Предупреждения больше показываться не будут, кроме каждых 10 подсчётов.")
        return

    if text.lower() in ['крипто/бай бонус 20', 'депозит бонус 10']:
        user_choice_data[user_id] = text.lower()
        await update.message.reply_text(f"Выбран: {text}. Теперь введи сумму.")
        return

    if user_id in user_choice_data:
        choice = user_choice_data[user_id]
        parts = text.replace(",", ".").split()
        results = []

        for part in parts:
            try:
                amount = float(part)
            except ValueError:
                continue  # пропускаем нечисловые значения

            if choice == 'депозит бонус 10':
                bonus = amount * 0.10
                wager = bonus * 15
            elif choice == 'крипто/бай бонус 20':
                bonus = amount * 0.20
                wager = bonus * 20
            else:
                continue

            slots = wager + amount
            roulette = wager * 3.33 + amount
            blackjack = wager * 5 + amount
            crash = wager * 10 + amount

            results.append(
                f"Сумма: {format_number(amount)} сомов\n"
                f"🔹 Слоты (100%) — {format_number(slots)}\n"
                f"🔹 Roulette (30%) — {format_number(roulette)}\n"
                f"🔹 Blackjack (20%) — {format_number(blackjack)}\n"
                f"🔹 Crash/другое (10%) — {format_number(crash)}\n"
            )

        if results:
            await update.message.reply_text("Результаты расчёта:\n\n" + "\n".join(results))
        else:
            await update.message.reply_text("Не удалось распознать ни одной суммы. Введите числа корректно.")

        user_count_calc[user_id] = user_count_calc.get(user_id, 0) + 1
        count = user_count_calc[user_id]

        if user_spam_status.get(user_id, True):
            await update.message.reply_text(
                "Обязательно перепроверяйте итоговые суммы! Это для вашей же страховки. "
                "Если хотите отключить это сообщение — напишите stopspam."
            )
        elif count % 10 == 0:
            await update.message.reply_text(
                "Обязательно перепроверяйте итоговые суммы! Это для вашей же страховки."
            )
    else:
        await update.message.reply_text("Сначала выбери бонус кнопкой ниже.", reply_markup=markup)

if __name__ == '__main__':
    app = ApplicationBuilder().token(os.environ.get("BOT_TOKEN")).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('status', status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()
