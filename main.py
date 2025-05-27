from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import os
import math

user_choice_data = {}
user_active_status = {}
user_spam_status = {}
user_count_calc = {}
user_authenticated = {}

PASSWORD = "starzbetbot"

reply_keyboard = [['Крипто/Бай бонус 20'], ['Депозит бонус 10']]
markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)

def format_number(n):
    return f"{math.ceil(n):,}".replace(",", " ")

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
    status_msg = "Бот сейчас активен." if user_active_status.get(user_id, True) else "Бот сейчас остановлен. Напиши /start чтобы включить."
    await update.message.reply_text(status_msg)

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

    if user_id not in user_choice_data:
        await update.message.reply_text("Сначала выбери бонус кнопкой ниже.", reply_markup=markup)
        return

    choice = user_choice_data[user_id]
    parts = text.replace(",", ".").split()
    valid_sums = []

    for part in parts:
        try:
            valid_sums.append(float(part))
        except ValueError:
            continue

    if not valid_sums:
        await update.message.reply_text("Пожалуйста, введи одну или несколько корректных сумм.")
        return

    is_plural = len(valid_sums) > 1
    intro = (
        "Для выполнения условий отыгрыша с вашими суммами бонуса потребуется сделать следующие объёмы ставок в разных играх:\n\n"
        if is_plural else
        "Для выполнения условий отыгрыша с вашей суммой бонуса потребуется сделать следующие объёмы ставок в разных играх:\n\n"
    )

    results = [intro]

    for idx, sums in enumerate(valid_sums, 1):
        if choice == 'депозит бонус 10':
            bonus = sums * 0.10
            wager = bonus * 15
        elif choice == 'крипто/бай бонус 20':
            bonus = sums * 0.20
            wager = bonus * 20
        else:
            continue

        slots = wager + sums
        roulette = wager * 3.33 + sums
        blackjack = wager * 5 + sums
        crash = wager * 10 + sums

        if is_plural:
            results.append(f"— **Сумма {idx}: {format_number(sums)} сомов**")
        results.append(
            f"🔹 Слоты (100%) — отыграть {format_number(slots)} сомов\n"
            f"🔹 Roulette (30%) — отыграть {format_number(roulette)} сомов\n"
            f"🔹 Blackjack (20%) — отыграть {format_number(blackjack)} сомов\n"
            f"🔹 Остальные настольные, crash игры и лайв-казино игры (10%) — отыграть {format_number(crash)} сомов\n"
        )

    await update.message.reply_text("\n".join(results), parse_mode="Markdown")

    user_count_calc[user_id] = user_count_calc.get(user_id, 0) + 1
    if user_spam_status.get(user_id, True):
        await update.message.reply_text(
            "Обязательно перепроверяйте итоговые суммы! Это для вашей же страховки. "
            "Если не хотите больше получать это сообщение — напишите stopspam"
        )
    elif user_count_calc[user_id] % 10 == 0:
        await update.message.reply_text(
            "Обязательно перепроверяйте итоговые суммы! Это для вашей же страховки."
        )

if __name__ == '__main__':
    app = ApplicationBuilder().token(os.environ.get("BOT_TOKEN")).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('status', status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()
    
