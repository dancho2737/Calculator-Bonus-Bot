from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import os
import math

# === Данные пользователей ===
user_language = {}
user_authenticated = {}
user_choice_data = {}
user_active_status = {}
user_spam_status = {}
user_count_calc = {}

PASSWORD = "starzbot"

# === Переводы ===
translations = {
    "ru": {
        "choose_language": "Выберите язык:",
        "enter_password": "Введите пароль для доступа к боту:",
        "wrong_password": "Неверный пароль. Повторите попытку.",
        "access_granted": "Доступ разрешён! Выбери бонус и введи сумму:",
        "bot_active": "Бот активирован. Выбери бонус для расчёта и введи сумму:",
        "bot_stopped": "Бот остановлен. Чтобы запустить снова, напиши /start.",
        "stopspam": "Предупреждения больше показываться не будут, кроме каждых 10 подсчётов.",
        "choose_bonus_first": "Сначала выбери бонус кнопкой ниже.",
        "invalid_number": "Пожалуйста, введи корректное число или числа.",
        "reminder": "Обязательно перепроверяйте итоговые суммы! Это для вашей же страховки.",
        "reminder_stopspam": "Если же хотите чтобы это сообщение больше не появлялось, то напишите stopspam",
        "bot_now_active": "Бот сейчас активен.",
        "bot_now_inactive": "Бот сейчас остановлен. Напиши /start чтобы включить.",
        "language_changed": "Язык успешно изменён. Введите пароль снова:"
    },
    "en": {
        "choose_language": "Choose your language:",
        "enter_password": "Enter the password to access the bot:",
        "wrong_password": "Incorrect password. Try again.",
        "access_granted": "Access granted! Choose a bonus and enter the amount:",
        "bot_active": "Bot activated. Choose a bonus to calculate and enter the amount:",
        "bot_stopped": "Bot stopped. Type /start to restart.",
        "stopspam": "You will no longer receive warnings, except every 10 calculations.",
        "choose_bonus_first": "Please choose a bonus using the button below first.",
        "invalid_number": "Please enter a valid number or numbers.",
        "reminder": "Always double-check the final amounts! It's for your safety.",
        "reminder_stopspam": "To stop seeing this message, type stopspam.",
        "bot_now_active": "Bot is currently active.",
        "bot_now_inactive": "Bot is currently inactive. Type /start to activate.",
        "language_changed": "Language changed. Please enter the password again:"
    },
    "tr": {
        "choose_language": "Lütfen dilinizi seçin:",
        "enter_password": "Bota erişmek için şifreyi girin:",
        "wrong_password": "Hatalı şifre. Lütfen tekrar deneyin.",
        "access_granted": "Erişim sağlandı! Bonus seç ve miktarı gir:",
        "bot_active": "Bot aktif. Hesaplama için bonusu seç ve miktarı gir:",
        "bot_stopped": "Bot durduruldu. Yeniden başlatmak için /start yaz.",
        "stopspam": "Uyarılar artık yalnızca her 10 hesaplamada bir gösterilecektir.",
        "choose_bonus_first": "Lütfen önce aşağıdaki butonlardan bir bonus seçin.",
        "invalid_number": "Lütfen geçerli bir sayı veya sayılar girin.",
        "reminder": "Son tutarları her zaman iki kez kontrol edin! Bu sizin güvenliğiniz içindir.",
        "reminder_stopspam": "Bu mesajı bir daha görmek istemiyorsanız 'stopspam' yazın.",
        "bot_now_active": "Bot şu anda aktif.",
        "bot_now_inactive": "Bot şu anda durdurulmuş. Başlatmak için /start yazın.",
        "language_changed": "Dil değiştirildi. Lütfen tekrar şifre girin:"
    }
}

def t(user_id, key):
    lang = user_language.get(user_id, 'ru')
    return translations[lang][key]

def get_user_lang(user_id):
    return user_language.get(user_id, 'ru')

def get_markup(lang):
    if lang == 'en':
        keyboard = [['Crypto/Buy Bonus 20'], ['Deposit Bonus 10']]
    elif lang == 'tr':
        keyboard = [['Kripto/Buy Bonusu 20'], ['Yatırım Bonusu 10']]
    else:
        keyboard = [['Крипто/Бай бонус 20'], ['Депозит бонус 10']]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def format_number(n):
    n_ceil = math.ceil(n)
    return f"{n_ceil:,}".replace(",", " ")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_authenticated[user_id] = False
    await update.message.reply_text(
        translations['ru']['choose_language'],
        reply_markup=ReplyKeyboardMarkup([['Русский', 'English', 'Türkçe']], resize_keyboard=True)
    )

async def handle_language_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang_map = {
        'Русский': 'ru',
        'English': 'en',
        'Türkçe': 'tr'
    }
    choice = update.message.text.strip()
    if choice in lang_map:
        user_language[user_id] = lang_map[choice]
        await update.message.reply_text(t(user_id, 'enter_password'))
    elif not user_authenticated.get(user_id, False):
        await update.message.reply_text(translations['ru']['choose_language'])

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    lang = get_user_lang(user_id)

    if not user_authenticated.get(user_id):
        if text == PASSWORD:
            user_authenticated[user_id] = True
            user_active_status[user_id] = True
            user_spam_status[user_id] = True
            user_count_calc[user_id] = 0
            await update.message.reply_text(t(user_id, 'access_granted'), reply_markup=get_markup(lang))
        else:
            await update.message.reply_text(t(user_id, 'wrong_password'))
        return

    if not user_active_status.get(user_id, True):
        return

    if text.lower() == "stop":
        user_active_status[user_id] = False
        await update.message.reply_text(t(user_id, 'bot_stopped'))
        return

    if text.lower() == "stopspam":
        user_spam_status[user_id] = False
        await update.message.reply_text(t(user_id, 'stopspam'))
        return

    lower_text = text.lower()
    bonuses = {
        'ru': ['крипто/бай бонус 20', 'депозит бонус 10'],
        'en': ['crypto/buy bonus 20', 'deposit bonus 10'],
        'tr': ['kripto/buy bonusu 20', 'yatırım bonusu 10']
    }

    if lower_text in [b.lower() for b in bonuses[lang]]:
        user_choice_data[user_id] = lower_text
        await update.message.reply_text(f"{text} ✅")
        return

    if user_id in user_choice_data:
        choice = user_choice_data[user_id]
        try:
            sums = [float(s.replace(',', '.')) for s in text.split()]
        except ValueError:
            await update.message.reply_text(t(user_id, 'invalid_number'))
            return

        is_plural = len(sums) > 1
        results = []

        for num in sums:
            if 'депозит' in choice or 'deposit' in choice or 'yatırım' in choice:
                bonus = num * 0.10
                wager = bonus * 15
            elif 'крипто' in choice or 'crypto' in choice or 'kripto' in choice:
                bonus = num * 0.20
                wager = bonus * 20
            else:
                continue

            slots = wager + num
            roulette = wager * 3.33 + num
            blackjack = wager * 5 + num
            crash = wager * 10 + num

            results.append(
                f"{t(user_id, 'bot_active')}\n"
                f"Сумма: {format_number(num)}\n"
                f"🔹 Слоты (100%) — {format_number(slots)}\n"
                f"🔹 Roulette (30%) — {format_number(roulette)}\n"
                f"🔹 Blackjack (20%) — {format_number(blackjack)}\n"
                f"🔹 Crash (10%) — {format_number(crash)}"
            )

        await update.message.reply_text("\n\n".join(results))

        user_count_calc[user_id] = user_count_calc.get(user_id, 0) + 1
        count = user_count_calc[user_id]

        if user_spam_status.get(user_id, True):
            await update.message.reply_text(f"{t(user_id, 'reminder')} {t(user_id, 'reminder_stopspam')}")
        else:
            if count % 10 == 0:
                await update.message.reply_text(t(user_id, 'reminder'))
    else:
        await update.message.reply_text(t(user_id, 'choose_bonus_first'), reply_markup=get_markup(lang))

async def handle_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not user_language.get(user_id):
        await handle_language_choice(update, context)
    else:
        await handle_message(update, context)

async def change_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_authenticated[user_id] = False
    await update.message.reply_text(
        translations['ru']['choose_language'],
        reply_markup=ReplyKeyboardMarkup([['Русский', 'English', 'Türkçe']], resize_keyboard=True)
    )

if __name__ == '__main__':
    app = ApplicationBuilder().token(os.environ.get("BOT_TOKEN")).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('language', change_language))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_router))

    app.run_polling()
