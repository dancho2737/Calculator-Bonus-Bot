from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import os
import math

# Пользовательские данные
user_lang = {}
user_choice_data = {}
user_active_status = {}
user_spam_status = {}
user_count_calc = {}
user_authenticated = {}

PASSWORD = "starzbot"

# Доступные языки
LANGUAGES = {
    'Русский': 'ru',
    'English': 'en',
    'Türkçe': 'tr'
}

# Переводы
translations = {
    "choose_lang": {
        "ru": "Выберите язык:",
        "en": "Choose your language:",
        "tr": "Dil seçin:"
    },
    "enter_password": {
        "ru": "Введите пароль для доступа к боту:",
        "en": "Enter the password to access the bot:",
        "tr": "Bota erişmek için şifreyi girin:"
    },
    "wrong_password": {
        "ru": "Неверный пароль. Повторите попытку.",
        "en": "Wrong password. Try again.",
        "tr": "Yanlış şifre. Tekrar deneyin."
    },
    "access_granted": {
        "ru": "Доступ разрешён! Выбери бонус и введи сумму:",
        "en": "Access granted! Choose a bonus and enter the amount:",
        "tr": "Erişim sağlandı! Bir bonus seçin ve miktarı girin:"
    },
    "bot_active": {
        "ru": "Бот активирован. Выбери бонус для расчёта и введи сумму:",
        "en": "Bot activated. Choose a bonus and enter the amount:",
        "tr": "Bot etkinleştirildi. Bonus seçin ve miktarı girin:"
    },
    "bot_now_active": {
        "ru": "Бот сейчас активен.",
        "en": "The bot is currently active.",
        "tr": "Bot şu anda aktif."
    },
    "bot_now_inactive": {
        "ru": "Бот сейчас остановлен. Напиши /start чтобы включить.",
        "en": "The bot is stopped. Type /start to activate it.",
        "tr": "Bot durduruldu. Yeniden başlatmak için /start yazın."
    },
    "bonus_selected": {
        "ru": "Выбран: {bonus}. Теперь введи сумму.",
        "en": "Selected: {bonus}. Now enter the amount.",
        "tr": "Seçildi: {bonus}. Şimdi miktarı girin."
    },
    "invalid_number": {
        "ru": "Пожалуйста, введи корректное число или числа.",
        "en": "Please enter a valid number or numbers.",
        "tr": "Lütfen geçerli bir sayı veya sayılar girin."
    },
    "check_warning": {
        "ru": "Обязательно перепроверяйте итоговые суммы! Это для вашей же страховки. Если же хотите чтобы это сообщение больше не появлялось, то напишите stopspam",
        "en": "Double-check your final amounts! It's for your own safety. If you want this message to stop showing, type stopspam",
        "tr": "Sonuçları tekrar kontrol edin! Bu sizin güvenliğiniz içindir. Bu mesajın artık görünmesini istemiyorsanız 'stopspam' yazın"
    },
    "check_every_10": {
        "ru": "Обязательно перепроверяйте итоговые суммы! Это для вашей же страховки.",
        "en": "Please double-check your final amounts! It's for your own safety.",
        "tr": "Lütfen sonuçları tekrar kontrol edin! Bu sizin güvenliğiniz içindir."
    },
    "choose_bonus_first": {
        "ru": "Сначала выбери бонус кнопкой ниже.",
        "en": "Please choose a bonus using the button below first.",
        "tr": "Lütfen önce aşağıdaki düğmeden bir bonus seçin."
    }
}

def t(key, lang):
    return translations.get(key, {}).get(lang, translations[key]['ru'])

def format_number(n):
    n_ceil = math.ceil(n)
    return f"{n_ceil:,}".replace(",", " ")

# Языковые клавиатуры
lang_keyboard = ReplyKeyboardMarkup([[KeyboardButton(l)] for l in LANGUAGES], resize_keyboard=True)
reply_keyboard = {
    'ru': ReplyKeyboardMarkup([['Крипто/Бай бонус 20'], ['Депозит бонус 10']], resize_keyboard=True),
    'en': ReplyKeyboardMarkup([['Crypto/Bai Bonus 20'], ['Deposit Bonus 10']], resize_keyboard=True),
    'tr': ReplyKeyboardMarkup([['Kripto/Bai Bonusu 20'], ['Depozito Bonusu 10']], resize_keyboard=True),
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_lang:
        await update.message.reply_text(t("choose_lang", "ru"), reply_markup=lang_keyboard)
        return

    lang = user_lang[user_id]

    if not user_authenticated.get(user_id):
        await update.message.reply_text(t("enter_password", lang))
        return

    user_active_status[user_id] = True
    user_spam_status[user_id] = True
    user_count_calc[user_id] = 0

    await update.message.reply_text(t("bot_active", lang), reply_markup=reply_keyboard[lang])

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = user_lang.get(user_id, 'ru')

    if not user_authenticated.get(user_id):
        await update.message.reply_text(t("enter_password", lang))
        return

    is_active = user_active_status.get(user_id, True)
    await update.message.reply_text(t("bot_now_active" if is_active else "bot_now_inactive", lang))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # Языковой выбор
    if text in LANGUAGES:
        user_lang[user_id] = LANGUAGES[text]
        await start(update, context)
        return

    lang = user_lang.get(user_id, 'ru')

    if not user_authenticated.get(user_id):
        if text == PASSWORD:
            user_authenticated[user_id] = True
            user_active_status[user_id] = True
            user_spam_status[user_id] = True
            user_count_calc[user_id] = 0
            await update.message.reply_text(t("access_granted", lang), reply_markup=reply_keyboard[lang])
        else:
            await update.message.reply_text(t("wrong_password", lang))
        return

    if not user_active_status.get(user_id, True):
        return

    if text.lower() == "stop":
        user_active_status[user_id] = False
        await update.message.reply_text(t("bot_now_inactive", lang))
        return

    if text.lower() == "stopspam":
        user_spam_status[user_id] = False
        await update.message.reply_text(t("check_every_10", lang))
        return

    bonuses = {
        'ru': ['крипто/бай бонус 20', 'депозит бонус 10'],
        'en': ['crypto/bai bonus 20', 'deposit bonus 10'],
        'tr': ['kripto/bai bonusu 20', 'depozito bonusu 10']
    }

    if text.lower() in bonuses[lang]:
        user_choice_data[user_id] = text.lower()
        await update.message.reply_text(t("bonus_selected", lang).format(bonus=text), reply_markup=reply_keyboard[lang])
        return

    if user_id in user_choice_data:
        choice = user_choice_data[user_id]
        try:
            sums = [float(s.replace(',', '.')) for s in text.split()]
        except ValueError:
            await update.message.reply_text(t("invalid_number", lang))
            return

        is_plural = len(sums) > 1
        results = []

        for num in sums:
            if choice.endswith('10'):
                sums2 = num * 0.10
                sums3 = sums2 * 15
            elif choice.endswith('20'):
                sums2 = num * 0.20
                sums3 = sums2 * 20
            else:
                continue

            slots = sums3 + num
            roulette = sums3 * 3.33 + num
            blackjack = sums3 * 5 + num
            crash = sums3 * 10 + num

            results.append(
                f"{'Сумма' if lang=='ru' else 'Amount'}: {format_number(num)}\n"
                f"🔹 Slots (100%) — {format_number(slots)}\n"
                f"🔹 Roulette (30%) — {format_number(roulette)}\n"
                f"🔹 Blackjack (20%) — {format_number(blackjack)}\n"
                f"🔹 {'Другие игры' if lang=='ru' else 'Other games'} (10%) — {format_number(crash)}"
            )

        intro = (
            "Для выполнения условий отыгрыша потребуется:\n" if lang == 'ru' else
            "To meet the wagering conditions, you need to:\n" if lang == 'en' else
            "Çevrim şartları için gerekli miktarlar:\n"
        )

        await update.message.reply_text(intro + "\n\n".join(results))

        user_count_calc[user_id] = user_count_calc.get(user_id, 0) + 1
        count = user_count_calc[user_id]

        if user_spam_status.get(user_id, True):
            await update.message.reply_text(t("check_warning", lang))
        else:
            if count % 10 == 0:
                await update.message.reply_text(t("check_every_10", lang))
    else:
        await update.message.reply_text(t("choose_bonus_first", lang), reply_markup=reply_keyboard[lang])

# Запуск бота
if __name__ == '__main__':
    app = ApplicationBuilder().token(os.environ.get("BOT_TOKEN")).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('status', status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()
