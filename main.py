from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, ConversationHandler

# Состояния для ConversationHandler
LANG, PASSWORD, BONUS_TYPE, SUMS_INPUT = range(4)

# Пароль
PASSWORD_CORRECT = "starzbot"

# Тексты на трёх языках
TEXTS = {
    'ru': {
        'ask_password': "Введите пароль:",
        'wrong_password': "Неверный пароль. Попробуйте ещё раз.",
        'choose_bonus': "Выберите тип бонуса:\n1. Крипто бонус 20%\n2. Бай бонус 20%\n3. Депозитный бонус 10%",
        'ask_sum': "Введите сумму(ы) для расчёта (можно несколько через пробел):",
        'stopspam_enabled': "Сообщения предупреждения отключены. Чтобы включить — напишите /spam",
        'stopspam_disabled': "Сообщения предупреждения включены.",
        'spam_message': "Обязательно проверяйте свои итоговые суммы! Это для вашей же страховки.",
        'invalid_sum': "Пожалуйста, введите корректное число или несколько чисел через пробел.",
    },
    'en': {
        'ask_password': "Enter the password:",
        'wrong_password': "Wrong password. Try again.",
        'choose_bonus': "Choose bonus type:\n1. Crypto bonus 20%\n2. Buy bonus 20%\n3. Deposit bonus 10%",
        'ask_sum': "Enter amount(s) for calculation (multiple allowed separated by space):",
        'stopspam_enabled': "Warning messages disabled. To enable, type /spam",
        'stopspam_disabled': "Warning messages enabled.",
        'spam_message': "Always check your final sums! This is for your own safety.",
        'invalid_sum': "Please enter a valid number or multiple numbers separated by spaces.",
    },
    'tr': {
        'ask_password': "Parolayı girin:",
        'wrong_password': "Yanlış parola. Tekrar deneyin.",
        'choose_bonus': "Bonus türünü seçin:\n1. Kripto bonus %20\n2. Bay bonus %20\n3. Mevduat bonusu %10",
        'ask_sum': "Hesaplama için miktar(lar) girin (birden fazlası aralarına boşluk koyarak):",
        'stopspam_enabled': "Uyarı mesajları kapatıldı. Açmak için /spam yazın",
        'stopspam_disabled': "Uyarı mesajları açıldı.",
        'spam_message': "Her zaman nihai tutarları kontrol edin! Bu sizin güvenliğiniz için.",
        'invalid_sum': "Lütfen geçerli bir sayı veya boşluklarla ayrılmış birden fazla sayı girin.",
    }
}

BONUS_PERCENT = {
    '1': 0.20,  # Crypto bonus 20%
    '2': 0.20,  # Buy bonus 20%
    '3': 0.10,  # Deposit bonus 10%
}

def format_number(num):
    return f"{num:,}".replace(',', ' ')

def get_bets_text(lang, slots, roulette, blackjack, crash):
    if lang == 'ru':
        text = (
            "Для выполнения условий отыгрыша с вашей суммой бонуса потребуется сделать следующие объёмы ставок в разных играх:\n\n"
            f"🔹 Слоты (100%) — отыграть {format_number(slots)} сомов\n\n"
            f"🔹 Roulette (30%) — отыграть {format_number(roulette)} сомов\n\n"
            f"🔹 Blackjack (20%) — отыграть {format_number(blackjack)} сомов\n\n"
            f"🔹 Остальные настольные, crash игры и лайв-казино игры (10%) — отыграть {format_number(crash)} сомов"
        )
    elif lang == 'en':
        text = (
            "To meet the wagering requirements with your bonus amount, you need to place bets in the following games:\n\n"
            f"🔹 Slots (100%) — wager {format_number(slots)} som\n\n"
            f"🔹 Roulette (30%) — wager {format_number(roulette)} som\n\n"
            f"🔹 Blackjack (20%) — wager {format_number(blackjack)} som\n\n"
            f"🔹 Other table, crash and live casino games (10%) — wager {format_number(crash)} som"
        )
    elif lang == 'tr':
        text = (
            "Bonus tutarınızla çevrim şartlarını yerine getirmek için aşağıdaki oyunlarda şu bahis miktarlarını yapmanız gerekir:\n\n"
            f"🔹 Slotlar (100%) — {format_number(slots)} som bahis\n\n"
            f"🔹 Rulet (30%) — {format_number(roulette)} som bahis\n\n"
            f"🔹 Blackjack (20%) — {format_number(blackjack)} som bahis\n\n"
            f"🔹 Diğer masa oyunları, crash ve canlı casino oyunları (10%) — {format_number(crash)} som bahis"
        )
    else:
        text = "Language not supported."
    return text

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Запускаем диалог, просим выбрать язык
    keyboard = [['Русский', 'English', 'Türkçe']]
    await update.message.reply_text(
        "Выберите язык / Choose language / Dil seçin:",
        reply_markup=None
    )
    return LANG

async def lang_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    if 'рус' in text:
        context.user_data['lang'] = 'ru'
    elif 'eng' in text:
        context.user_data['lang'] = 'en'
    elif 'türk' in text or 'turk' in text:
        context.user_data['lang'] = 'tr'
    else:
        # Неизвестный язык
        await update.message.reply_text("Пожалуйста, выберите язык из списка.")
        return LANG

    await update.message.reply_text(TEXTS[context.user_data['lang']]['ask_password'])
    return PASSWORD

async def password_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.strip() == PASSWORD_CORRECT:
        await update.message.reply_text(TEXTS[context.user_data['lang']]['choose_bonus'])
        return BONUS_TYPE
    else:
        await update.message.reply_text(TEXTS[context.user_data['lang']]['wrong_password'])
        return PASSWORD

async def bonus_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text.strip()
    if choice not in BONUS_PERCENT:
        await update.message.reply_text(TEXTS[context.user_data['lang']]['choose_bonus'])
        return BONUS_TYPE
    context.user_data['bonus_percent'] = BONUS_PERCENT[choice]
    await update.message.reply_text(TEXTS[context.user_data['lang']]['ask_sum'])
    # Инициализируем счетчик спам-сообщений и флаг
    context.user_data.setdefault('spam_counter', 0)
    context.user_data.setdefault('stop_spam', False)
    return SUMS_INPUT

async def sums_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get('lang', 'ru')
    text = update.message.text.strip()
    parts = text.split()
    numbers = []
    for part in parts:
        try:
            n = int(part.replace(' ', ''))
            if n > 0:
                numbers.append(n)
        except:
            pass
    if not numbers:
        await update.message.reply_text(TEXTS[lang]['invalid_sum'])
        return SUMS_INPUT

    total = sum(numbers)
    bonus_percent = context.user_data.get('bonus_percent', 0.10)

    sums2 = total * bonus_percent
    sums3 = sums2 * 15
    slots = sums3 + total
    roulette = sums3 * 3.33 + total
    blackjack = sums3 * 5 + total
    crash = sums3 * 10 + total

    message = get_bets_text(lang, int(slots), int(roulette), int(blackjack), int(crash))

    # Спам-сообщения
    spam_counter = context.user_data.get('spam_counter', 0) + 1
    context.user_data['spam_counter'] = spam_counter
    stop_spam = context.user_data.get('stop_spam', False)

    await update.message.reply_text(message)

    if not stop_spam or (spam_counter % 7 == 0):
        await update.message.reply_text(TEXTS[lang]['spam_message'])

    return SUMS_INPUT

async def stopspam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get('lang', 'ru')
    context.user_data['stop_spam'] = True
    await update.message.reply_text(TEXTS[lang]['stopspam_enabled'])

async def spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get('lang', 'ru')
    context.user_data['stop_spam'] = False
    await update.message.reply_text(TEXTS[lang]['stopspam_disabled'])

async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Выберите язык / Choose language / Dil seçin:")
    return LANG

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Выход из диалога.")
    return ConversationHandler.END

def main():
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    if not TOKEN:
        raise ValueError("TELEGRAM_TOKEN is not set in environment variables.")

    app = ApplicationBuilder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start), CommandHandler('lang', lang_command)],
        states={
            LANG: [MessageHandler(filters.TEXT & ~filters.COMMAND, lang_choice)],
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, password_check)],
            BONUS_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, bonus_choice)],
            SUMS_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, sums_input)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True,
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("stopspam", stopspam))
    app.add_handler(CommandHandler("spam", spam))

    app.run_polling()

if __name__ == '__main__':
    main()
    
