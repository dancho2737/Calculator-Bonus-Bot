import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)

LANGUAGE, PASSWORD, BONUS_SELECTION, AMOUNT = range(4)
user_data = {}

LANGUAGES = {
    'Русский': 'ru',
    'English': 'en',
    'Türkçe': 'tr'
}

TEXTS = {
    'ru': {
        'choose_language': 'Выберите язык:',
        'enter_password': 'Введите пароль:',
        'wrong_password': 'Неверный пароль. Попробуйте снова.',
        'password_ok': 'Пароль верный. Выберите бонус:',
        'choose_bonus': 'Выберите тип бонуса:',
        'enter_amount': 'Введите сумму (можно через пробел):',
        'invalid_input': 'Пожалуйста, введите только числа через пробел.',
        'results': 'Для выполнения условий отыгрыша с вашей суммой бонуса потребуется сделать следующие объёмы ставок в разных играх:'

🔹 Слоты (100%) — отыграть {slots} сомов
🔹 Roulette (30%) — отыграть {roulette} сомов
🔹 Blackjack (20%) — отыграть {blackjack} сомов
🔹 Остальные настольные, crash игры и лайв-казино игры (10%) — отыграть {crash} сомов',
        'reminder': 'Обязательно проверяйте свои итоговые суммы! Это для вашей же страховки.',
        'stop_reminder': 'Сообщение об осторожности отключено.',
        'lang_changed': 'Язык изменён. Выберите новый язык:',
    },
    'en': {
        'choose_language': 'Choose your language:',
        'enter_password': 'Enter the password:',
        'wrong_password': 'Wrong password. Try again.',
        'password_ok': 'Correct password. Choose a bonus:',
        'choose_bonus': 'Select bonus type:',
        'enter_amount': 'Enter amount (you can separate with space):',
        'invalid_input': 'Please enter only numbers separated by space.',
        'results': 'To meet the wagering requirements for your bonus amount, you need to wager the following amounts in various games:

🔹 Slots (100%) — wager {slots} soms
🔹 Roulette (30%) — wager {roulette} soms
🔹 Blackjack (20%) — wager {blackjack} soms
🔹 Other table games, crash, and live casino games (10%) — wager {crash} soms',
        'reminder': 'Always double-check your final amounts! This is for your safety.',
        'stop_reminder': 'Reminder message disabled.',
        'lang_changed': 'Language changed. Please choose a new language:',
    },
    'tr': {
        'choose_language': 'Dilini seçin:',
        'enter_password': 'Şifreyi girin:',
        'wrong_password': 'Yanlış şifre. Tekrar deneyin.',
        'password_ok': 'Doğru şifre. Bonus seçin:',
        'choose_bonus': 'Bonus türünü seçin:',
        'enter_amount': 'Tutarı girin (boşlukla ayırabilirsiniz):',
        'invalid_input': 'Lütfen sadece boşlukla ayrılmış sayılar girin.',
        'results': 'Bonus tutarınız için gereken çevrim hacmi aşağıdaki gibidir:

🔹 Slotlar (100%) — {slots} som bahis
🔹 Rulet (30%) — {roulette} som bahis
🔹 Blackjack (20%) — {blackjack} som bahis
🔹 Diğer masa, crash ve canlı casino oyunları (10%) — {crash} som bahis',
        'reminder': 'Son tutarlarınızı her zaman kontrol edin! Bu sizin için bir güvenliktir.',
        'stop_reminder': 'Uyarı mesajı devre dışı.',
        'lang_changed': 'Dil değiştirildi. Yeni bir dil seçin:',
    },
}

REMINDER_INTERVAL = 7

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[k] for k in LANGUAGES.keys()]
    await update.message.reply_text("Choose language / Выберите язык / Dilinizi seçin:",
                                    reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
    return LANGUAGE

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = LANGUAGES.get(update.message.text)
    if not lang:
        return LANGUAGE
    context.user_data['lang'] = lang
    context.user_data['count'] = 0
    context.user_data['show_reminder'] = True
    await update.message.reply_text(TEXTS[lang]['enter_password'])
    return PASSWORD

async def check_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data['lang']
    if update.message.text.strip() != "starzbot":
        await update.message.reply_text(TEXTS[lang]['wrong_password'])
        return PASSWORD
    keyboard = [["Бай бонус 20%"], ["Крипто бонус 20%"], ["Депозитный бонус 10%"]]
    await update.message.reply_text(TEXTS[lang]['password_ok'],
                                    reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
    return BONUS_SELECTION

async def set_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['bonus'] = update.message.text
    lang = context.user_data['lang']
    await update.message.reply_text(TEXTS[lang]['enter_amount'])
    return AMOUNT

async def calculate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data['lang']
    bonus = context.user_data['bonus']
    try:
        numbers = list(map(float, update.message.text.strip().split()))
    except:
        await update.message.reply_text(TEXTS[lang]['invalid_input'])
        return AMOUNT

    results = []
    for num in numbers:
        if "10%" in bonus:
            base = num * 0.10 * 15
        else:
            base = num * 0.20 * 15
        results.append({
            'slots': int(base + num),
            'roulette': int(base * 3.33 + num),
            'blackjack': int(base * 5 + num),
            'crash': int(base * 10 + num)
        })

    reply = ""
    for r in results:
        reply += TEXTS[lang]['results'].format(**r) + "\n\n"

    context.user_data['count'] += 1
    if context.user_data.get('show_reminder'):
        reply += TEXTS[lang]['reminder']
    if context.user_data['count'] % REMINDER_INTERVAL == 0:
        reply += f"\n\n{texts[lang]['reminder']}"

    await update.message.reply_text(reply)
    return AMOUNT

async def stopspam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['show_reminder'] = False
    lang = context.user_data.get('lang', 'ru')
    await update.message.reply_text(TEXTS[lang]['stop_reminder'])

async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[k] for k in LANGUAGES.keys()]
    await update.message.reply_text(TEXTS[context.user_data.get('lang', 'ru')]['lang_changed'],
                                    reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
    return LANGUAGE

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено.")
    return ConversationHandler.END

def main():
    import logging
    import os
    logging.basicConfig(level=logging.INFO)
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    if not TOKEN:
        raise ValueError("TELEGRAM_TOKEN is not set in environment variables.")

    app = ApplicationBuilder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANGUAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_language)],
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_password)],
            BONUS_SELECTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_bonus)],
            AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, calculate)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("stopspam", stopspam))
    app.add_handler(CommandHandler("lang", lang_command))

    app.run_polling()

if __name__ == '__main__':
    main()
    
