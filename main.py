from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import os

CHOOSING, TYPING_AMOUNT = range(2)

reply_keyboard = [['Бай бонус 20', 'Крипто бонус 20'], ['Депозит бонус 10']]
markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)

user_choice_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Выбери бонус для расчёта:",
        reply_markup=markup
    )
    return CHOOSING

async def choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_choice = update.message.text
    user_choice_data[update.effective_user.id] = user_choice
    await update.message.reply_text(f"Ты выбрал '{user_choice}'. Введи сумму:")
    return TYPING_AMOUNT

async def calculate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    amount_text = update.message.text

    try:
        sums = float(amount_text.replace(',', '.'))
    except ValueError:
        await update.message.reply_text("Пожалуйста, введи корректное число.")
        return TYPING_AMOUNT

    choice = user_choice_data.get(user_id)
    if not choice:
        await update.message.reply_text("Ошибка выбора. Пожалуйста, начни заново командой /start")
        return ConversationHandler.END

    if choice == 'Депозит бонус 10':
        sums2 = sums * 0.10
        sums3 = sums2 * 15
        result = (
            f"Слоты: {sums3 + sums:.2f}\n"
            f"Рулет: {sums3 * 3.33 + sums:.2f}\n"
            f"Блэкджэк: {sums3 * 5 + sums:.2f}\n"
            f"Crash игры: {sums3 * 10 + sums:.2f}"
        )
    elif choice in ['Бай бонус 20', 'Крипто бонус 20']:
        sums2 = sums * 0.20
        sums3 = sums2 * 20
        result = (
            f"Слоты: {sums3 + sums:.2f}\n"
            f"Рулет: {sums3 * 3.33 + sums:.2f}\n"
            f"Блэкджэк: {sums3 * 5 + sums:.2f}\n"
            f"Crash игры: {sums3 * 10 + sums:.2f}"
        )
    else:
        result = "Неизвестный бонус."

    await update.message.reply_text(f"Результаты для '{choice}':\n{result}")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отмена.")
    return ConversationHandler.END

if __name__ == '__main__':
    app = ApplicationBuilder().token(os.environ.get("BOT_TOKEN")).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING: [MessageHandler(filters.TEXT & ~filters.COMMAND, choice)],
            TYPING_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, calculate)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    app.add_handler(conv_handler)
    app.run_polling()
