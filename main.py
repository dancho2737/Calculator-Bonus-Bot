from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import os
import math

# Константы этапов ConversationHandler
LANGUAGE, PASSWORD = range(2)

user_choice_data = {}
user_active_status = {}
user_spam_status = {}
user_count_calc = {}
user_authenticated = {}
user_language = {}

PASSWORD_TEXT = {
    'ru': "Введите пароль для доступа к боту:",
    'en': "Enter the password to access the bot:",
    'tr': "Bota erişmek için şifreyi girin:"
}

PASSWORD = "starzbot"

reply_keyboard = {
    'ru': [['Крипто/Бай бонус 20'], ['Депозит бонус 10']],
    'en': [['Crypto/Buy Bonus 20'], ['Deposit Bonus 10']],
    'tr': [['Kripto/Bay Bonus 20'], ['Mevduat Bonusu 10']],
}

markup_dict = {
    lang: ReplyKeyboardMarkup(reply_keyboard[lang], resize_keyboard=True) for lang in reply_keyboard
}

LANGUAGE_KEYBOARD = ReplyKeyboardMarkup([['Русский', 'English', 'Türkçe']], one_time_keyboard=True, resize_keyboard=True)

def format_number(n):
    n_ceil = math.ceil(n)
    return f"{n_ceil:,}".replace(",", " ")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # Запрос выбора языка
    await update.message.reply_text(
        "Выберите язык / Choose language / Dil seçin:",
        reply_markup=LANGUAGE_KEYBOARD
    )
    return LANGUAGE

async def language_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.lower()
    if text.startswith('рус'):
        user_language[user_id] = 'ru'
    elif text.startswith('eng'):
        user_language[user_id] = 'en'
    elif text.startswith('tür'):
        user_language[user_id] = 'tr'
    else:
        # По умолчанию русский
        user_language[user_id] = 'ru'

    lang = user_language[user_id]
    await update.message.reply_text(PASSWORD_TEXT[lang], reply_markup=ReplyKeyboardRemove())
    return PASSWORD

async def password_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = user_language.get(user_id, 'ru')
    text = update.message.text.strip()

    if text == PASSWORD:
        user_authenticated[user_id] = True
        user_active_status[user_id] = True
        user_spam_status[user_id] = True
        user_count_calc[user_id] = 0

        await update.message.reply_text(
            {
                'ru': "Доступ разрешён! Выбери бонус и введи сумму:",
                'en': "Access granted! Choose a bonus and enter the amount:",
                'tr': "Erişim sağlandı! Bir bonus seçin ve miktarı girin:"
            }[lang],
            reply_markup=markup_dict[lang]
        )
        return ConversationHandler.END
    else:
        await update.message.reply_text(
            {
                'ru': "Неверный пароль. Повторите попытку.",
                'en': "Incorrect password. Please try again.",
                'tr': "Yanlış şifre. Lütfen tekrar deneyin."
            }[lang]
        )
        return PASSWORD

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = user_language.get(user_id, 'ru')

    if not user_authenticated.get(user_id):
        await update.message.reply_text(
            {
                'ru': "Сначала введите пароль. Напиши /start.",
                'en': "Please enter password first. Type /start.",
                'tr': "Önce şifreyi girin. /start yazın."
            }[lang]
        )
        return

    is_active = user_active_status.get(user_id, True)
    await update.message.reply_text(
        {
            'ru': "Бот сейчас активен." if is_active else "Бот сейчас остановлен. Напиши /start чтобы включить.",
            'en': "Bot is active now." if is_active else "Bot is stopped now. Write /start to activate.",
            'tr': "Bot şu anda aktif." if is_active else "Bot şu anda durduruldu. Başlatmak için /start yazın."
        }[lang]
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = user_language.get(user_id, 'ru')
    text = update.message.text.strip()

    if not user_authenticated.get(user_id):
        await update.message.reply_text(
            {
                'ru': "Пожалуйста, сначала используйте /start чтобы начать и ввести пароль.",
                'en': "Please use /start first to begin and enter password.",
                'tr': "Lütfen önce /start komutunu kullanarak başlayın ve şifreyi girin."
            }[lang]
        )
        return

    if not user_active_status.get(user_id, True):
        return

    if text.lower() == "stop":
        user_active_status[user_id] = False
        await update.message.reply_text(
            {
                'ru': "Бот остановлен. Чтобы запустить снова, напиши /start.",
                'en': "Bot stopped. To start again, type /start.",
                'tr': "Bot durduruldu. Tekrar başlatmak için /start yazın."
            }[lang]
        )
        return

    if text.lower() == "stopspam":
        user_spam_status[user_id] = False
        await update.message.reply_text(
            {
                'ru': "Предупреждения больше показываться не будут, кроме каждых 10 подсчётов.",
                'en': "Warnings will no longer be shown, except every 10 calculations.",
                'tr': "Uyarılar artık gösterilmeyecek, sadece her 10 hesaplamada bir."
            }[lang]
        )
        return

    bonuses = {
        'ru': ['крипто/бай бонус 20', 'депозит бонус 10'],
        'en': ['crypto/buy bonus 20', 'deposit bonus 10'],
        'tr': ['kripto/bay bonus 20', 'mevduat bonusu 10'],
    }

    if text.lower() in bonuses[lang]:
        user_choice_data[user_id] = text.lower()
        await update.message.reply_text(
            {
                'ru': f"Выбран: {text}. Теперь введи сумму.",
                'en': f"Selected: {text}. Now enter the amount.",
                'tr': f"Seçildi: {text}. Şimdi miktarı girin."
            }[lang]
        )
        return

    if user_id in user_choice_data:
        choice = user_choice_data[user_id]
        try:
            sums = [float(s.replace(',', '.')) for s in text.split()]
        except ValueError:
            await update.message.reply_text(
                {
                    'ru': "Пожалуйста, введи корректное число или числа.",
                    'en': "Please enter a valid number or numbers.",
                    'tr': "Lütfen geçerli bir sayı veya sayılar girin."
                }[lang]
            )
            return

        results = []
        for num in sums:
            if choice == bonuses[lang][1]:  # депозит бонус 10
                bonus = num * 0.10
                required = bonus * 15
            elif choice == bonuses[lang][0]:  # крипто/бай бонус 20
                bonus = num * 0.20
                required = bonus * 20
            else:
                continue

            slots = required + num
            roulette = required * 3.33 + num
            blackjack = required * 5 + num
            crash = required * 10 + num

            results.append(
                f"Сумма: {format_number(num)} сомов\n"
                f"🔹 Слоты (100%) — отыграть {format_number(slots)} сомов\n"
                f"🔹 Roulette (30%) — отыграть {format_number(roulette)} сомов\n"
                f"🔹 Blackjack (20%) — отыграть {format_number(blackjack)} сомов\n"
                f"🔹 Остальные настольные, crash игры и лайв-казино игры (10%) — отыграть {format_number(crash)} сомов"
            )

        intro = {
            'ru': "Для выполнения условий отыгрыша с вашими суммами бонуса потребуется сделать следующие объёмы ставок в разных играх:\n",
            'en': "To meet the wagering requirements for your bonus amounts, you will need to place the following bets in different games:\n",
            'tr': "Bonus tutarları için çevrim şartlarını karşılamak amacıyla farklı oyunlarda yapılması gereken bahis miktarları:\n"
        }[lang]

        result_text = intro + "\n\n".join(results)
        await update.message.reply_text(result_text)

        user_count_calc[user_id] = user_count_calc.get(user_id, 0) + 1
        count = user_count_calc[user_id]

        if user_spam_status.get(user_id, True):
            await update.message.reply_text(
                {
                    'ru': "Обязательно перепроверяйте итоговые суммы! Это для вашей же страховки. Если же хотите чтобы это сообщение больше не появлялось, то напишите stopspam",
                    'en': "Please double-check the final amounts! This is for your own protection. If you want to stop seeing this message, type stopspam",
                    'tr': "Lütfen nihai tutarları tekrar kontrol edin! Bu sizin güvenliğiniz için. Bu mesajın tekrar görünmemesini istiyorsanız stopspam yazın."
                }[lang]
            )
        else:
            if count % 10 == 0:
                await update.message.reply_text(
                    {
                        'ru': "Обязательно перепроверяйте итоговые суммы! Это для вашей же страховки.",
                        'en': "Please double-check the final amounts! This is for your own protection.",
                        'tr': "Lütfen nihai tutarları tekrar kontrol edin! Bu sizin güvenliğiniz için."
                    }[lang]
                )
    else:
        await update.message.reply_text(
            {
                'ru': "Сначала выбери бонус кнопкой ниже.",
                'en': "First choose a bonus with the button below.",
                'tr': "Önce aşağıdaki butondan bir bonus seçin."
            }[lang],
            reply_markup=markup_dict.get(lang)
        )

async def change_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(
        "Выберите язык / Choose language / Dil seçin:",
        reply_markup=LANGUAGE_KEYBOARD
    )
    return LANGUAGE

def main():
    app = ApplicationBuilder().token(os.environ.get("BOT_TOKEN")).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            LANGUAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, language_handler)],
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, password_handler)],
        },
        fallbacks=[]
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler('status', status))
    app.add_handler(CommandHandler('lang', change_language))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()

if __name__ == '__main__':
    main()
