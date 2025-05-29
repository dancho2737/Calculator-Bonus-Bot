from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import os
import math

user_choice_data = {}
user_active_status = {}
user_spam_status = {}
user_count_calc = {}
user_authenticated = {}
user_language = {}

PASSWORD = "starzbot"

lang_keyboard = [['Русский', 'English', 'Türkçe']]
lang_markup = ReplyKeyboardMarkup(lang_keyboard, resize_keyboard=True)

reply_keyboards = {
    'ru': [['Крипто/Бай бонус 20'], ['Депозит бонус 10']],
    'en': [['Crypto/Bai Bonus 20'], ['Deposit Bonus 10']],
    'tr': [['Kripto/Bai Bonusu 20'], ['Depozito Bonusu 10']]
}

def format_number(n):
    n_ceil = math.ceil(n)
    return f"{n_ceil:,}".replace(",", " ")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not user_authenticated.get(user_id):
        await update.message.reply_text("Введите пароль для доступа к боту:")
        return

    await update.message.reply_text("Выберите язык / Select a language / Dil seçin:", reply_markup=lang_markup)

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
            await update.message.reply_text("Выберите язык / Select a language / Dil seçin:", reply_markup=lang_markup)
        else:
            await update.message.reply_text("Неверный пароль. Повторите попытку.")
        return

    if text.lower() in ['русский', 'russian']:
        lang = 'ru'
    elif text.lower() in ['english', 'английский']:
        lang = 'en'
    elif text.lower() in ['turkish', 'türkçe', 'турецкий']:
        lang = 'tr'
    else:
        lang = user_language.get(user_id, 'ru')

    user_language[user_id] = lang

    reply_markup = ReplyKeyboardMarkup(reply_keyboards[lang], resize_keyboard=True)

    if text.lower() in ['русский', 'english', 'turkish', 'английский', 'турецкий', 'russian', 'türkçe']:
        if lang == 'ru':
            msg = "Бот активирован. Выбери бонус для расчёта и введи сумму:"
        elif lang == 'en':
            msg = "Bot activated. Choose a bonus and enter the amount:"
        elif lang == 'tr':
            msg = "Bot etkinleştirildi. Bir bonus seçin ve miktarı girin:"
        await update.message.reply_text(msg, reply_markup=reply_markup)
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

    choice_map = {
        'ru': ['крипто/бай бонус 20', 'депозит бонус 10'],
        'en': ['crypto/bai bonus 20', 'deposit bonus 10'],
        'tr': ['kripto/bai bonusu 20', 'depozito bonusu 10']
    }

    for key in choice_map.get(lang, []):
        if text.lower() == key:
            user_choice_data[user_id] = key
            await update.message.reply_text(f"Выбран: {text}. Теперь введи сумму.")
            return

    if user_id in user_choice_data:
        choice = user_choice_data[user_id]
        try:
            sums = [float(s.replace(',', '.')) for s in text.split()]
        except ValueError:
            await update.message.reply_text("Пожалуйста, введи корректное число или числа.")
            return

        is_plural = len(sums) > 1
        results = []

        for num in sums:
            if 'депозит' in choice or 'deposit' in choice or 'depozito' in choice:
                sums2 = num * 0.10
                sums3 = sums2 * 15
            elif 'крипто' in choice or 'crypto' in choice or 'kripto' in choice:
                sums2 = num * 0.20
                sums3 = sums2 * 20
            else:
                continue

            slots = sums3 + num
            roulette = sums3 * 3.33 + num
            blackjack = sums3 * 5 + num
            crash = sums3 * 10 + num

            results.append((num, slots, roulette, blackjack, crash))

        if lang == 'ru':
            intro = (
                "Для выполнения условий отыгрыша с вашими суммами бонуса потребуется сделать следующие объёмы ставок в разных играх:\n"
                if is_plural else
                "Для выполнения условий отыгрыша с вашей суммой бонуса потребуется сделать следующие объёмы ставок в разных играх:\n"
            )
            currency = "сомов"
            lines = [
                f"Сумма: {format_number(num)} {currency}\n"
                f"🔹 Слоты (100%) — отыграть {format_number(slots)} {currency}\n"
                f"🔹 Roulette (30%) — отыграть {format_number(roulette)} {currency}\n"
                f"🔹 Blackjack (20%) — отыграть {format_number(blackjack)} {currency}\n"
                f"🔹 Остальные настольные, crash игры и лайв-казино игры (10%) — отыграть {format_number(crash)} {currency}"
                for num, slots, roulette, blackjack, crash in results
            ]
        elif lang == 'en':
            intro = (
                "To meet the wagering conditions with your bonus amounts, you need to place the following bets in different games:\n"
                if is_plural else
                "To meet the wagering conditions with your bonus amount, you need to place the following bets in different games:\n"
            )
            currency = "som(s)"
            lines = [
                f"Amount: {format_number(num)} {currency}\n"
                f"🔹 Slots (100%) — wager {format_number(slots)} {currency}\n"
                f"🔹 Roulette (30%) — wager {format_number(roulette)} {currency}\n"
                f"🔹 Blackjack (20%) — wager {format_number(blackjack)} {currency}\n"
                f"🔹 Other table, crash and live-casino games (10%) — wager {format_number(crash)} {currency}"
                for num, slots, roulette, blackjack, crash in results
            ]
        elif lang == 'tr':
            intro = (
                "Bonus miktarlarınızla çevrim şartlarını karşılamak için aşağıdaki oyun türlerinde şu miktarlarda bahis yapmanız gerekir:\n"
                if is_plural else
                "Bonus miktarınızla çevrim şartlarını karşılamak için aşağıdaki oyun türlerinde şu miktarda bahis yapmanız gerekir:\n"
            )
            currency = "som"
            lines = [
                f"Tutar: {format_number(num)} {currency}\n"
                f"🔹 Slotlar (100%) — {format_number(slots)} {currency} bahis\n"
                f"🔹 Rulet (30%) — {format_number(roulette)} {currency} bahis\n"
                f"🔹 Blackjack (20%) — {format_number(blackjack)} {currency} bahis\n"
                f"🔹 Diğer masa, crash ve canlı casino oyunları (10%) — {format_number(crash)} {currency} bahis"
                for num, slots, roulette, blackjack, crash in results
            ]

        result_text = intro + "\n\n".join(lines)
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
        await update.message.reply_text("Сначала выбери бонус кнопкой ниже.", reply_markup=ReplyKeyboardMarkup(reply_keyboards[lang], resize_keyboard=True))

if __name__ == '__main__':
    app = ApplicationBuilder().token(os.environ.get("BOT_TOKEN")).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('status', status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()
