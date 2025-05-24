from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import os

user_choice_data = {}

reply_keyboard = [['Крипто/Бай бонус 20'], ['Депозит бонус 10']]
markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Выбери бонус для расчёта и введи сумму:",
        reply_markup=markup
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if text in ['Крипто/Бай бонус 20', 'Депозит бонус 10']:
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

        if choice == 'Депозит бонус 10':
            sums2 = sums * 0.10
            sums3 = sums2 * 15
        elif choice == 'Крипто/Бай бонус 20':
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
            f"🔹 Слоты (100%) — отыграть {slots:.2f} сомов\n"
            f"🔹 Roulette (30%) — отыграть {roulette:.2f} сомов\n"
            f"🔹 Blackjack (20%) — отыграть {blackjack:.2f} сомов\n"
            f"🔹 Остальные настольные, crash игры и лайв-казино игры (10%) — отыграть {crash:.2f} сомов"
        )

        await update.message.reply_text(result)
    else:
        await update.message.reply_text("Сначала выбери бонус кнопкой ниже.", reply_markup=markup)

if __name__ == '__main__':
    app = ApplicationBuilder().token(os.environ.get("BOT_TOKEN")).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()
    
