from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import os
import math

user_choice_data = {}
user_active_status = {}
user_spam_status = {}
user_count_calc = {}
user_authenticated = {}

PASSWORD = "starzbot"

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
        try:
            # обработка нескольких чисел, разделённых пробелом
            sums = [float(s.replace(',', '.')) for s in text.split()]
        except ValueError:
            await update.message.reply_text("Пожалуйста, введи корректное число или числа.")
            return

        is_plural = len(sums) > 1
        results = []

        for num in sums:
            if choice == 'депозит бонус 10':
                sums2 = num * 0.10
                sums3 = sums2 * 15
            elif choice == 'крипто/бай бонус 20':
                sums2 = num * 0.20
                sums3 = sums2 * 20
            else:
                continue

            slots = sums3 + num
            roulette = sums3 * 3.33 + num
            blackjack = sums3 * 5 + num
            crash = sums3 * 10 + num

            results.append(
                f"Сумма: {format_number(num)} сомов\n"
                f"🔹 Слоты (100%) — отыграть {format_number(slots)} сомов\n"
                f"🔹 Roulette (30%) — отыграть {format_number(roulette)} сомов\n"
                f"🔹 Blackjack (20%) — отыграть {format_number(blackjack)} сомов\n"
                f"🔹 Остальные настольные, crash игры и лайв-казино игры (10%) — отыграть {format_number(crash)} сомов"
            )

        intro = (
            "Для выполнения условий отыгрыша с вашими суммами бонуса потребуется сделать следующие объёмы ставок в разных играх:\n"
            if is_plural else
            "Для выполнения условий отыгрыша с вашей суммой бонуса потребуется сделать следующие объёмы ставок в разных играх:\n"
        )

        result_text = intro + "\n\n".join(results)
        await update.message.reply_text(result_text)

        user_count_calc[user_id] = user_count_calc.get(user_id, 0) + 1
        count = user_count_calc[user_id]

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
        await update.message.reply_text("Сначала выбери бонус кнопкой ниже.", reply_markup=markup)

if __name__ == '__main__':
    app = ApplicationBuilder().token(os.environ.get("BOT_TOKEN")).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('status', status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()
                 
