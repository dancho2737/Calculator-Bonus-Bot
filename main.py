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

translations = {
    'ru': {
        'enter_password': "Введите пароль для доступа к боту:",
        'access_granted': "Доступ разрешён! Выбери бонус и введи сумму:",
        'bot_activated': "Бот активирован. Выбери бонус для расчёта и введи сумму:",
        'choose_bonus': "Выбери бонус для расчёта и введи сумму:",
        'bonus_crypto': "Крипто/Бай бонус 20",
        'bonus_deposit': "Депозит бонус 10",
        'wrong_password': "Неверный пароль. Повторите попытку.",
        'choose_bonus_button': "Сначала выбери бонус кнопкой ниже.",
        'bot_stopped': "Бот сейчас остановлен. Напиши /start чтобы включить.",
        'bot_active': "Бот сейчас активен.",
        'stop_message': "Бот остановлен. Чтобы запустить снова, напиши /start.",
        'stopspam_message': "Предупреждения больше показываться не будут, кроме каждых 10 подсчётов.",
        'check_sums': ("Обязательно перепроверяйте итоговые суммы! Это для вашей же страховки. "
                       "Если же хотите чтобы это сообщение больше не появлялось, то напишите stopspam"),
        'check_sums_short': "Обязательно перепроверяйте итоговые суммы! Это для вашей же страховки.",
        'invalid_number': "Пожалуйста, введи корректное число или числа.",
        'wager_intro_single': "Для выполнения условий отыгрыша с вашей суммой бонуса потребуется сделать следующие объёмы ставок в разных играх:\n",
        'wager_intro_plural': "Для выполнения условий отыгрыша с вашими суммами бонуса потребуется сделать следующие объёмы ставок в разных играх:\n"
    },
    'en': {
        'enter_password': "Enter password to access the bot:",
        'access_granted': "Access granted! Choose a bonus and enter the amount:",
        'bot_activated': "Bot activated. Choose a bonus and enter the amount:",
        'choose_bonus': "Choose a bonus and enter the amount:",
        'bonus_crypto': "Crypto/Bai bonus 20",
        'bonus_deposit': "Deposit bonus 10",
        'wrong_password': "Wrong password. Please try again.",
        'choose_bonus_button': "Please choose a bonus using the button below first.",
        'bot_stopped': "Bot is stopped now. Type /start to activate.",
        'bot_active': "Bot is active now.",
        'stop_message': "Bot stopped. To start again, type /start.",
        'stopspam_message': "Warnings will no longer appear except every 10 counts.",
        'check_sums': ("Please double-check the final sums! This is for your own safety. "
                       "If you don't want to see this message again, type stopspam"),
        'check_sums_short': "Please double-check the final sums! This is for your own safety.",
        'invalid_number': "Please enter a valid number or numbers.",
        'wager_intro_single': "To meet the wagering conditions, you need to:\n",
        'wager_intro_plural': "To meet the wagering conditions, you need to:\n"
    },
    'tr': {
        'enter_password': "Bota erişim için şifreyi girin:",
        'access_granted': "Erişim verildi! Bir bonus seç ve miktarı gir:",
        'bot_activated': "Bot aktif edildi. Bir bonus seç ve miktarı gir:",
        'choose_bonus': "Bir bonus seç ve miktarı gir:",
        'bonus_crypto': "Kripto/Bay bonus 20",
        'bonus_deposit': "Depozito bonus 10",
        'wrong_password': "Yanlış şifre. Lütfen tekrar deneyin.",
        'choose_bonus_button': "Lütfen önce aşağıdaki butondan bir bonus seçin.",
        'bot_stopped': "Bot şu anda durduruldu. Başlatmak için /start yazın.",
        'bot_active': "Bot şu anda aktif.",
        'stop_message': "Bot durduruldu. Yeniden başlatmak için /start yazın.",
        'stopspam_message': "Uyarılar artık sadece 10 hesaplamada bir gösterilecek.",
        'check_sums': ("Lütfen nihai tutarları tekrar kontrol edin! Bu sizin güvenliğiniz için. "
                       "Bu mesajı tekrar görmek istemiyorsanız stopspam yazın"),
        'check_sums_short': "Lütfen nihai tutarları tekrar kontrol edin! Bu sizin güvenliğiniz için.",
        'invalid_number': "Lütfen geçerli bir sayı veya sayılar girin.",
        'wager_intro_single': "Oynatma koşullarını karşılamak için ihtiyacınız olan miktar:\n",
        'wager_intro_plural': "Oynatma koşullarını karşılamak için ihtiyacınız olan miktarlar:\n"
    }
}

def format_number(n):
    n_ceil = math.ceil(n)
    return f"{n_ceil:,}".replace(",", " ")

async def send_bonus_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = user_language.get(user_id, 'ru')
    reply_keyboard = [
        [translations[lang]['bonus_crypto']],
        [translations[lang]['bonus_deposit']]
    ]
    markup_bonus = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)
    await update.message.reply_text(
        translations[lang]['choose_bonus'],
        reply_markup=markup_bonus
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # При старте всегда сначала выбираем язык
    await language(update, context)
    # Сбрасываем состояние аутентификации, чтобы вводить пароль заново
    user_authenticated[user_id] = False

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not user_authenticated.get(user_id):
        lang = user_language.get(user_id, 'ru')
        await update.message.reply_text(translations[lang]['enter_password'])
        return

    is_active = user_active_status.get(user_id, True)
    lang = user_language.get(user_id, 'ru')
    await update.message.reply_text(
        translations[lang]['bot_active'] if is_active else translations[lang]['bot_stopped']
    )

async def language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_keyboard = [['Русский', 'English', 'Türkçe']]
    markup_lang = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)
    await update.message.reply_text("Choose your language / Язык / Dil seçin:", reply_markup=markup_lang)

async def language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    selected_lang = update.message.text

    if selected_lang == 'Русский':
        user_language[user_id] = 'ru'
    elif selected_lang == 'English':
        user_language[user_id] = 'en'
    elif selected_lang == 'Türkçe':
        user_language[user_id] = 'tr'
    else:
        await update.message.reply_text("Invalid language selection.")
        return

    # После выбора языка — просим ввести пароль на этом языке
    await update.message.reply_text(translations[user_language[user_id]]['enter_password'])

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    lang = user_language.get(user_id, 'ru')

    # Если не аутентифицирован — проверяем пароль
    if not user_authenticated.get(user_id):
        if text == PASSWORD:
            user_authenticated[user_id] = True
            user_active_status[user_id] = True
            user_spam_status[user_id] = True
            user_count_calc[user_id] = 0
            await update.message.reply_text(translations[lang]['access_granted'])
            await send_bonus_menu(update, context)
        else:
            await update.message.reply_text(translations[lang]['wrong_password'])
        return

    # Проверка состояния бота
    if not user_active_status.get(user_id, True):
        return

    # Обработка команд stop и stopspam
    if text.lower() == "stop":
        user_active_status[user_id] = False
        await update.message.reply_text(translations[lang]['stop_message'])
        return

    if text.lower() == "stopspam":
        user_spam_status[user_id] = False
        await update.message.reply_text(translations[lang]['stopspam_message'])
        return

    bonus_crypto = translations[lang]['bonus_crypto'].lower()
    bonus_deposit = translations[lang]['bonus_deposit'].lower()

    if text.lower() == bonus_crypto:
        user_choice_data[user_id] = bonus_crypto
        await update.message.reply_text(f"{translations[lang]['bonus_crypto']} выбран. Теперь введите сумму.")
        return
    elif text.lower() == bonus_deposit:
        user_choice_data[user_id] = bonus_deposit
        await update.message.reply_text(f"{translations[lang]['bonus_deposit']} выбран. Теперь введите сумму.")
        return

    if user_id in user_choice_data:
        choice = user_choice_data[user_id]
        try:
            sums = [float(s.replace(',', '.')) for s in text.split()]
        except ValueError:
            await update.message.reply_text(translations[lang]['invalid_number'])
            return

        is_plural = len(sums) > 1
        results = []

        for num in sums:
            if choice == bonus_deposit:
                sums2 = num * 0.10
                sums3 = sums2 * 15
            elif choice == bonus_crypto:
                sums2 = num * 0.20
                sums3 = sums2 * 20
            else:
                continue

            slots = sums3 + num
            roulette = sums3 * 3.33 + num
            blackjack = sums3 * 5 + num
            crash = sums3 * 10 + num

            if lang in ['en', 'tr']:
                results.append(
                    f"Amount: {format_number(num)} som\n"
                    f"🔹 Slots (100%) — {format_number(slots)} som\n"
                    f"🔹 Roulette (30%) — {format_number(roulette)} som\n"
                    f"🔹 Blackjack (20%) — {format_number(blackjack)} som\n"
                    f"🔹 Other games (10%) — {format_number(crash)} som"
                )
            else:
                results.append(
                    f"Сумма: {format_number(num)} сомов\n"
                    f"🔹 Слоты (100%) — отыграть {format_number(slots)} сомов\n"
                    f"🔹 Roulette (30%) — отыграть {format_number(roulette)} сомов\n"
                    f"🔹 Blackjack (20%) — отыграть {format_number(blackjack)} сомов\n"
                    f"🔹 Остальные настольные, crash игры и лайв-казино игры (10%) — отыграть {format_number(crash)} сомов"
                )

        intro = translations[lang]['wager_intro_plural'] if is_plural else translations[lang]['wager_intro_single']
        result_text = intro + "\n\n".join(results)
        await update.message.reply_text(result_text)

        user_count_calc[user_id] = user_count_calc.get(user_id, 0) + 1
        count = user_count_calc[user_id]

        if user_spam_status.get(user_id, True):
            await update.message.reply_text(translations[lang]['check_sums'])
        else:
            if count % 10 == 0:
                await update.message.reply_text(translations[lang]['check_sums_short'])
    else:
        await update.message.reply_text(translations[lang]['choose_bonus_button'])
        await send_bonus_menu(update, context)

if __name__ == '__main__':
