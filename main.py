from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackContext
import os
import math

user_choice_data = {}
user_active_status = {}
user_spam_status = {}
user_count_calc = {}
user_authenticated = {}
user_language = {}

PASSWORD = "starzbot"

LANGUAGE_KEYBOARD = ReplyKeyboardMarkup(
    [["🇷🇺 Русский", "🇬🇧 English", "🇹🇷 Türkçe"]],
    resize_keyboard=True
)

reply_keyboards = {
    "ru": [['Крипто/Бай бонус 20'], ['Депозит бонус 10']],
    "en": [['Crypto/Bai Bonus 20'], ['Deposit Bonus 10']],
    "tr": [['Kripto/Bai Bonusu 20'], ['Yatırım Bonusu 10']]
}

translations = {
    "choose_language": {
        "ru": "Пожалуйста, выбери язык:",
        "en": "Please choose your language:",
        "tr": "Lütfen dil seçiniz:"
    },
    "enter_password": {
        "ru": "Введите пароль для доступа к боту:",
        "en": "Enter the password to access the bot:",
        "tr": "Bota erişmek için şifreyi giriniz:"
    },
    "access_granted": {
        "ru": "Доступ разрешён! Выбери бонус и введи сумму:",
        "en": "Access granted! Choose a bonus and enter the amount:",
        "tr": "Erişim verildi! Bonusu seçin ve miktarı girin:"
    },
    "wrong_password": {
        "ru": "Неверный пароль. Повторите попытку.",
        "en": "Wrong password. Please try again.",
        "tr": "Yanlış şifre. Lütfen tekrar deneyin."
    },
    "bot_activated": {
        "ru": "Бот активирован. Выбери бонус для расчёта и введи сумму:",
        "en": "Bot activated. Choose a bonus to calculate and enter the amount:",
        "tr": "Bot aktif. Hesaplamak için bir bonus seçin ve miktarı girin:"
    },
    "bot_stopped": {
        "ru": "Бот остановлен. Чтобы запустить снова, напиши /start.",
        "en": "Bot stopped. To restart, type /start.",
        "tr": "Bot durduruldu. Yeniden başlatmak için /start yazın."
    },
    "stopspam_confirm": {
        "ru": "Предупреждения больше показываться не будут, кроме каждых 10 подсчётов.",
        "en": "Warnings will no longer appear, except every 10 calculations.",
        "tr": "Uyarılar artık gösterilmeyecek, yalnızca her 10 hesaplamada bir."
    },
    "choose_bonus": {
        "ru": "Выбран: {text}. Теперь введи сумму.",
        "en": "Selected: {text}. Now enter the amount.",
        "tr": "Seçildi: {text}. Şimdi miktarı girin."
    },
    "invalid_number": {
        "ru": "Пожалуйста, введи корректное число или числа.",
        "en": "Please enter a valid number or numbers.",
        "tr": "Lütfen geçerli bir sayı veya sayılar girin."
    },
    "reminder": {
        "ru": "Обязательно перепроверяйте итоговые суммы! Это для вашей же страховки. Если же хотите чтобы это сообщение больше не появлялось, то напишите stopspam",
        "en": "Always double-check the final amounts! It's for your own safety. If you want to stop seeing this message, type stopspam",
        "tr": "Toplamları her zaman tekrar kontrol edin! Bu sizin güvenliğiniz için. Bu mesajı artık görmek istemiyorsanız, stopspam yazın"
    },
    "reminder_short": {
        "ru": "Обязательно перепроверяйте итоговые суммы! Это для вашей же страховки.",
        "en": "Always double-check the final amounts! It's for your own safety.",
        "tr": "Toplamları her zaman tekrar kontrol edin! Bu sizin güvenliğiniz için."
    },
    "choose_bonus_first": {
        "ru": "Сначала выбери бонус кнопкой ниже.",
        "en": "Please choose a bonus using the button below.",
        "tr": "Lütfen aşağıdaki düğmeyi kullanarak bir bonus seçin."
    },
    "wager_intro_singular": {
        "ru": "Для выполнения условий отыгрыша с вашей суммой бонуса потребуется сделать следующие объёмы ставок в разных играх:",
        "en": "To meet the wagering conditions, you need to:",
        "tr": "Çevrim şartlarını karşılamak için şunları yapmalısınız:"
    },
    "wager_intro_plural": {
        "ru": "Для выполнения условий отыгрыша с вашими суммами бонуса потребуется сделать следующие объёмы ставок в разных играх:",
        "en": "To meet the wagering conditions for your bonuses, you need to:",
        "tr": "Bonuslarınız için çevrim şartlarını karşılamak için şunları yapmalısınız:"
    },
    "status_active": {
        "ru": "Бот сейчас активен.",
        "en": "The bot is currently active.",
        "tr": "Bot şu anda aktif."
    },
    "status_inactive": {
        "ru": "Бот сейчас остановлен. Напиши /start чтобы включить.",
        "en": "The bot is currently stopped. Type /start to activate it.",
        "tr": "Bot şu anda durdurulmuş. Etkinleştirmek için /start yazın."
    }
}

def format_number(n):
    n_ceil = math.ceil(n)
    return f"{n_ceil:,}".replace(",", " ")

def get_lang(user_id):
    return user_language.get(user_id, "ru")

def get_translation(key, lang):
    return translations.get(key, {}).get(lang, translations.get(key, {}).get("ru", key))

def generate_result_text(choice, sums, lang):
    is_plural = len(sums) > 1
    results = []
    for num in sums:
        if "депозит" in choice or "deposit" in choice.lower() or "yatırım" in choice.lower():
            sums2 = num * 0.10
            sums3 = sums2 * 15
        elif "крипто" in choice or "crypto" in choice.lower() or "kripto" in choice.lower():
            sums2 = num * 0.20
            sums3 = sums2 * 20
        else:
            continue
        slots = sums3 + num
        roulette = sums3 * 3.33 + num
        blackjack = sums3 * 5 + num
        crash = sums3 * 10 + num

        results.append(
            f"Amount: {format_number(num)} som\n"
            f"🔹 Slots (100%) — {format_number(slots)} som\n"
            f"🔹 Roulette (30%) — {format_number(roulette)} som\n"
            f"🔹 Blackjack (20%) — {format_number(blackjack)} som\n"
            f"🔹 Other games (10%) — {format_number(crash)} som"
        )
    intro = get_translation("wager_intro_plural" if is_plural else "wager_intro_singular", lang)
    return intro + "\n\n" + "\n\n".join(results)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_language[user_id] = None
    await update.message.reply_text("Пожалуйста, выбери язык / Please choose your language / Lütfen dil seçiniz:", reply_markup=LANGUAGE_KEYBOARD)

async def language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_language[user_id] = None
    await update.message.reply_text("Пожалуйста, выбери язык / Please choose your language / Lütfen dil seçiniz:", reply_markup=LANGUAGE_KEYBOARD)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if user_language.get(user_id) is None:
        if "рус" in text.lower():
            user_language[user_id] = "ru"
        elif "eng" in text.lower():
            user_language[user_id] = "en"
        elif "türk" in text.lower() or "turk" in text.lower():
            user_language[user_id] = "tr"
        else:
            await update.message.reply_text("Пожалуйста, выбери язык:", reply_markup=LANGUAGE_KEYBOARD)
            return
        lang = user_language[user_id]
        await update.message.reply_text(get_translation("enter_password", lang))
        return

    lang = get_lang(user_id)

    if not user_authenticated.get(user_id):
        if text == PASSWORD:
            user_authenticated[user_id] = True
            user_active_status[user_id] = True
            user_spam_status[user_id] = True
            user_count_calc[user_id] = 0
            await update.message.reply_text(get_translation("access_granted", lang), reply_markup=ReplyKeyboardMarkup(reply_keyboards[lang], resize_keyboard=True))
        else:
            await update.message.reply_text(get_translation("wrong_password", lang))
        return

    if not user_active_status.get(user_id, True):
        return

    if text.lower() == "stop":
        user_active_status[user_id] = False
        await update.message.reply_text(get_translation("bot_stopped", lang))
        return

    if text.lower() == "stopspam":
        user_spam_status[user_id] = False
        await update.message.reply_text(get_translation("stopspam_confirm", lang))
        return

    if text.lower() in sum(reply_keyboards.values(), []):
        user_choice_data[user_id] = text.lower()
        await update.message.reply_text(get_translation("choose_bonus", lang).format(text=text))
        return

    if user_id in user_choice_data:
        choice = user_choice_data[user_id]
        try:
            sums = [float(s.replace(',', '.')) for s in text.split()]
        except ValueError:
            await update.message.reply_text(get_translation("invalid_number", lang))
            return

        result_text = generate_result_text(choice, sums, lang)
        await update.message.reply_text(result_text)

        user_count_calc[user_id] = user_count_calc.get(user_id, 0) + 1
        count = user_count_calc[user_id]

        if user_spam_status.get(user_id, True):
            await update.message.reply_text(get_translation("reminder", lang))
        else:
            if count % 10 == 0:
                await update.message.reply_text(get_translation("reminder_short", lang))
    else:
        await update.message.reply_text(get_translation("choose_bonus_first", lang), reply_markup=ReplyKeyboardMarkup(reply_keyboards[lang], resize_keyboard=True))

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_lang(user_id)
    if not user_authenticated.get(user_id):
        await update.message.reply_text(get_translation("enter_password", lang))
        return
    is_active = user_active_status.get(user_id, True)
    await update.message.reply_text(get_translation("status_active" if is_active else "status_inactive", lang))

if __name__ == '__main__':
    app = ApplicationBuilder().token(os.environ.get("BOT_TOKEN")).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('language', language))
    app.add_handler(CommandHandler('status', status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()
