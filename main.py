from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import os
import math

# Хранение состояния пользователя
user_choice_data = {}
user_active_status = {}
user_spam_status = {}
user_count_calc = {}
user_authenticated = {}
user_language = {}

PASSWORD = "starzbot"

# Клавиатуры по языкам
keyboards = {
    "ru": [['Крипто/Бай бонус 20'], ['Депозит бонус 10']],
    "en": [['Crypto/Bai bonus 20'], ['Deposit bonus 10']],
    "tr": [['Kripto/Bay bonus 20'], ['Yatırım bonusu 10']]
}

# Словарь бонусов: ключ -> варианты текста на всех языках (для удобства)
bonus_keys = {
    "crypto_20": ["крипто/бай бонус 20", "crypto/bai bonus 20", "kripto/bay bonus 20"],
    "deposit_10": ["депозит бонус 10", "deposit bonus 10", "yatırım bonusu 10"]
}

# Сообщения на всех языках
messages = {
    "ru": {
        "ask_password": "Введите пароль для доступа к боту:",
        "access_granted": "Доступ разрешён! Выбери бонус и введи сумму:",
        "wrong_password": "Неверный пароль. Повторите попытку.",
        "bot_activated": "Бот активирован. Выбери бонус для расчёта и введи сумму:",
        "choose_bonus": "Сначала выбери бонус кнопкой ниже.",
        "bot_stopped": "Бот сейчас остановлен. Напиши /start чтобы включить.",
        "bot_active": "Бот сейчас активен.",
        "stop_message": "Бот остановлен. Чтобы запустить снова, напиши /start.",
        "stopspam_message": "Предупреждения больше показываться не будут, кроме каждых 10 подсчётов.",
        "invalid_number": "Пожалуйста, введи корректное число или числа.",
        "check_sums": ("Обязательно перепроверяйте итоговые суммы! Это для вашей же страховки. "
                       "Если же хотите чтобы это сообщение больше не появлялось, то напишите stopspam"),
        "check_sums_10": "Обязательно перепроверяйте итоговые суммы! Это для вашей же страховки.",
        "wager_intro_plural": "Для выполнения условий отыгрыша с вашими суммами бонуса потребуется сделать следующие объёмы ставок в разных играх:\n",
        "wager_intro_singular": "Для выполнения условий отыгрыша с вашей суммой бонуса потребуется сделать следующие объёмы ставок в разных играх:\n",
        "amount": "Сумма: {amount}",
        "slots": "🔹 Слоты (100%) — отыграть {value} сом",
        "roulette": "🔹 Roulette (30%) — отыграть {value} сом",
        "blackjack": "🔹 Blackjack (20%) — отыграть {value} сом",
        "other_games": "🔹 Остальные настольные, crash игры и лайв-казино игры (10%) — отыграть {value} сом",
        "language_prompt": "Выберите язык / Choose language / Dil seçin:",
        "language_changed": "Язык изменён на русский.",
    },
    "en": {
        "ask_password": "Enter the password to access the bot:",
        "access_granted": "Access granted! Choose a bonus and enter the amount:",
        "wrong_password": "Wrong password. Please try again.",
        "bot_activated": "Bot activated. Choose a bonus and enter the amount:",
        "choose_bonus": "Please choose a bonus using the buttons below first.",
        "bot_stopped": "Bot is stopped now. Send /start to activate.",
        "bot_active": "Bot is active now.",
        "stop_message": "Bot stopped. To start again, send /start.",
        "stopspam_message": "Warnings will no longer appear except every 10 calculations.",
        "invalid_number": "Please enter a valid number or numbers.",
        "check_sums": ("Be sure to double-check the final amounts! This is for your own protection. "
                       "If you want this message to stop appearing, type stopspam"),
        "check_sums_10": "Be sure to double-check the final amounts! This is for your own protection.",
        "wager_intro_plural": "To meet the wagering conditions, you need to:",
        "wager_intro_singular": "To meet the wagering conditions, you need to:",
        "amount": "Amount: {amount} som",
        "slots": "🔹 Slots (100%) — {value} som",
        "roulette": "🔹 Roulette (30%) — {value} som",
        "blackjack": "🔹 Blackjack (20%) — {value} som",
        "other_games": "🔹 Other games (10%) — {value} som",
        "language_prompt": "Please choose your language / Выберите язык / Dil seçin:",
        "language_changed": "Language changed to English.",
    },
    "tr": {
        "ask_password": "Bota erişmek için şifreyi girin:",
        "access_granted": "Erişim verildi! Bir bonus seçin ve tutarı girin:",
        "wrong_password": "Yanlış şifre. Lütfen tekrar deneyin.",
        "bot_activated": "Bot etkinleştirildi. Bir bonus seçin ve tutarı girin:",
        "choose_bonus": "Lütfen önce aşağıdaki butonlardan bir bonus seçin.",
        "bot_stopped": "Bot şu anda durduruldu. Başlatmak için /start yazın.",
        "bot_active": "Bot şu anda aktif.",
        "stop_message": "Bot durduruldu. Tekrar başlatmak için /start yazın.",
        "stopspam_message": "Uyarılar artık yalnızca her 10 hesaplamada bir gösterilecek.",
        "invalid_number": "Lütfen geçerli bir sayı veya sayılar girin.",
        "check_sums": ("Nihai tutarları mutlaka tekrar kontrol edin! Bu sizin güvenliğiniz için. "
                       "Bu mesajın görünmemesini istiyorsanız, stopspam yazın"),
        "check_sums_10": "Nihai tutarları mutlaka tekrar kontrol edin! Bu sizin güvenliğiniz için.",
        "wager_intro_plural": "Kazanç şartlarını yerine getirmek için şunları yapmanız gerekecek:",
        "wager_intro_singular": "Kazanç şartlarını yerine getirmek için şunları yapmanız gerekecek:",
        "amount": "Tutar: {amount} som",
        "slots": "🔹 Slotlar (100%) — {value} som",
        "roulette": "🔹 Rulet (30%) — {value} som",
        "blackjack": "🔹 Blackjack (20%) — {value} som",
        "other_games": "🔹 Diğer oyunlar (10%) — {value} som",
        "language_prompt": "Lütfen dilinizi seçin / Please choose your language / Выберите язык:",
        "language_changed": "Dil Türkçe olarak değiştirildi.",
    }
}

def format_number(n):
    n_ceil = math.ceil(n)
    return f"{n_ceil:,}".replace(",", " ")

async def ask_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_language[user_id] = None  # Сброс языка
    keyboard = ReplyKeyboardMarkup([['Русский', 'English', 'Türkçe']], resize_keyboard=True)
    await update.message.reply_text(messages["ru"]["language_prompt"], reply_markup=keyboard)

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.lower()

    if text == 'русский':
        user_language[user_id] = "ru"
        await update.message.reply_text(messages["ru"]["language_changed"])
    elif text == 'english':
        user_language[user_id] = "en"
        await update.message.reply_text(messages["en"]["language_changed"])
    elif text == 'türkçe' or text == 'turkce':
        user_language[user_id] = "tr"
        await update.message.reply_text(messages["tr"]["language_changed"])
    else:
        await update.message.reply_text("Пожалуйста, выберите язык из предложенных вариантов.")
        return

    # После выбора языка попросим ввести пароль
    await update.message.reply_text(messages[user_language[user_id]]["ask_password"], reply_markup=ReplyKeyboardMarkup([], resize_keyboard=True))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = user_language.get(user_id)

    if lang is None:
        # Если язык не выбран, попросим выбрать
        await ask_language(update, context)
        return

    if not user_authenticated.get(user_id):
        await update.message.reply_text(messages[lang]["ask_password"])
        return

    user_active_status[user_id] = True
    user_spam_status[user_id] = True
    user_count_calc[user_id] = 0

    await update.message.reply_text(
        messages[lang]["bot_activated"],
        reply_markup=ReplyKeyboardMarkup(keyboards[lang], resize_keyboard=True)
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = user_language.get(user_id, "ru")
    if not user_authenticated.get(user_id):
        await update.message.reply_text(messages[lang]["ask_password"])
        return

    is_active = user_active_status.get(user_id, True)
    await update.message.reply_text(messages[lang]["bot_active"] if is_active else messages[lang]["bot_stopped"])

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    lang = user_language.get(user_id, "ru")

    # Обработка выбора языка (если не выбран)
    if lang is None:
        await set_language(update, context)
        return

    # Проверка пароля
    if not user_authenticated.get(user_id):
        if text == PASSWORD:
            user_authenticated[user_id] = True
            user_active_status[user_id] = True
            user_spam_status[user_id] = True
            user_count_calc[user_id] = 0
            await update.message.reply_text(messages[lang]["access_granted"], reply_markup=ReplyKeyboardMarkup(keyboards[lang], resize_keyboard=True))
        else:
            await update.message.reply_text(messages[lang]["wrong_password"])
        return

    if not user_active_status.get(user_id, True):
        return

    # Управляющие команды (stop, stopspam)
    if text.lower() == "stop":
        user_active_status[user_id] = False
        await update.message.reply_text(messages[lang]["stop_message"])
        return

    if text.lower() == "stopspam":
        user_spam_status[user_id] = False
        await update.message.reply_text(messages[lang]["stopspam_message"])
        return

    # Проверка выбора бонуса
    choice_key = None
    for key, variants in bonus_keys.items():
        if text.lower() in [v.lower() for v in variants]:
            choice_key = key
            break

    if choice_key:
        user_choice_data[user_id] = choice_key
        await update.message.reply_text(f"{text}. {messages[lang]['amount'].format(amount='Теперь введи сумму.')}")
        return

    # Обработка суммы
    if user_id in user_choice_data:
        choice = user_choice_data[user_id]
        try:
            sums = [float(s.replace(',', '.')) for s in text.split()]
        except ValueError:
            await update.message.reply_text(messages[lang]["invalid_number"])
            return

        is_plural = len(sums) > 1
        results = []

        for num in sums:
            if choice == 'deposit_10':
                sums2 = num * 0.10
                sums3 = sums2 * 15
            elif choice == 'crypto_20':
                sums2 = num * 0.20
                sums3 = sums2 * 20
            else:
                continue

            slots = sums3 + num
            roulette = sums3 * 3.33 + num
            blackjack = sums3 * 5 + num
            crash = sums3 * 10 + num

            results.append(
                f"{messages[lang]['amount'].format(amount=format_number(num))}\n"
                f"{messages[lang]['slots'].format(value=format_number(slots))}\n"
                f"{messages[lang]['roulette'].format(value=format_number(roulette))}\n"
                f"{messages[lang]['blackjack'].format(value=format_number(blackjack))}\n"
                f"{messages[lang]['other_games'].format(value=format_number(crash))}"
            )

        intro = messages[lang]["wager_intro_plural"] if is_plural else messages[lang]["wager_intro_singular"]
        result_text = intro + "\n\n".join(results)
        await update.message.reply_text(result_text)

        user_count_calc[user_id] = user_count_calc.get(user_id, 0) + 1
        count = user_count_calc[user_id]

        if user_spam_status.get(user_id, True):
            await update.message.reply_text(messages[lang]["check_sums"])
        else:
            if count % 10 == 0:
                await update.message.reply_text(messages[lang]["check_sums_10"])

    else:
        await update.message.reply_text(messages[lang]["choose_bonus"], reply_markup=ReplyKeyboardMarkup(keyboards[lang], resize_keyboard=True))


if __name__ == '__main__':
    app = ApplicationBuilder().token(os.environ.get("BOT_TOKEN")).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('status', status))
    app.add_handler(CommandHandler('language', ask_language))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()
