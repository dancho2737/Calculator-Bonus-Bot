from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import os
import math

user_choice_data = {}
user_active_status = {}

reply_keyboard = [['Крипто/Бай бонус 20'], ['Депозит бонус 10']]
markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)

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
            f"Для выполнения условий отыгрыша с вашей суммой бонуса потребуется сделать следующие объёмы ставок в разных играх:\n\n"
            f"🔹 Слоты (100%) — отыграть {math.ceil(slots)} сомов\n"
            f"🔹 Roulette (30%) — отыграть {math.ceil(roulette)} сомов\n"
            f"🔹 Blackjack (20%) — отыграть {math.ceil(blackjack)} сомов\n"
            f"🔹 Остальные настольные, crash игры и лайв-казино игры (10%) — отыграть {math.ceil(crash)} сомов"
        )

        await update.message.reply_text(result)
    else:
        await update.message.reply_text("Сначала выбери бонус кнопкой ниже.", reply_markup=markup)

if name == 'main':
    app = ApplicationBuilder().token(os.environ.get("BOT_TOKEN")).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('status', status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()
