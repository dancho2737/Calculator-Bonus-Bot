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

# Клавиатуры для каждого языка
keyboards = {
    'ru': [['Крипто/Бай бонус 20'], ['Депозит бонус 10']],
    'en': [['Crypto/Bai bonus 20'], ['Deposit bonus 10']],
    'tr': [['Kripto/Bay bonus 20'], ['Yatırım bonusu 10']]
}

# Тексты сообщений для разных языков
MESSAGES = {
    'password_prompt': {
        'ru': "Введите пароль для доступа к боту:",
        'en': "Please enter the password to access the bot:",
        'tr': "Bota erişmek için lütfen şifreyi girin:"
    },
    'password_wrong': {
        'ru': "Неверный пароль. Повторите попытку.",
        'en': "Wrong password. Please try again.",
        'tr': "Yanlış şifre. Lütfen tekrar deneyin."
    },
    'access_granted': {
        'ru': "Доступ разрешён! Выбери бонус и введи сумму:",
        'en': "Access granted! Choose a bonus and enter the amount:",
        'tr': "Erişim onaylandı! Bir bonus seçin ve tutarı girin:"
    },
    'bot_activated': {
        'ru': "Бот активирован. Выбери бонус для расчёта и введи сумму:",
        'en': "Bot activated. Choose a bonus for calculation and enter the amount:",
        'tr': "Bot etkinleştirildi. Hesaplama için bonus seçin ve tutarı girin:"
    },
    'choose_bonus': {
        'ru': "Сначала выбери бонус кнопкой ниже.",
        'en': "First, choose a bonus with the button below.",
        'tr': "Önce aşağıdaki butondan bir bonus seçin."
    },
    'stop_message': {
        'ru': "Бот остановлен. Чтобы запустить снова, напиши /start.",
        'en': "Bot stopped. To start again, type /start.",
        'tr': "Bot durduruldu. Yeniden başlatmak için /start yazın."
    },
    'stopspam_message': {
        'ru': "Предупреждения больше показываться не будут, кроме каждых 10 подсчётов.",
        'en': "Warnings will no longer be shown, except every 10 calculations.",
        'tr': "Uyarılar artık gösterilmeyecek, sadece her 10 hesaplamada bir gösterilecek."
    },
    'calc_warning': {
        'ru': "Обязательно перепроверяйте итоговые суммы! Это для вашей же страховки. Если же хотите чтобы это сообщение больше не появлялось, то напишите stopspam",
        'en': "Be sure to double-check the final amounts! This is for your own safety. If you want this message to stop appearing, type stopspam",
        'tr': "Son tutarları mutlaka tekrar kontrol edin! Bu sizin güvenliğiniz için. Bu mesajın tekrar görünmesini istemiyorsanız, stopspam yazın"
    },
    'calc_warning_10': {
        'ru': "Обязательно перепроверяйте итоговые суммы! Это для вашей же страховки.",
        'en': "Be sure to double-check the final amounts! This is for your own safety.",
        'tr': "Son tutarları mutlaka tekrar kontrol edin! Bu sizin güvenliğiniz için."
    },
    'enter_language': {
        'ru': "Выберите язык / Choose language / Dil seçin:",
        'en': "Select language / Выберите язык / Dil seçin:",
        'tr': "Dil seçin / Выберите язык / Select language:"
    },
    'language_changed': {
        'ru': "Язык изменён на русский.",
        'en': "Language changed to English.",
        'tr': "Dil Türkçe olarak değiştirildi."
    }
}

LANGUAGE_CODES = ['ru', 'en', 'tr']

BONUSES = {
    'ru': ['крипто/бай бонус 20', 'депозит бонус 10'],
    'en': ['crypto/bai bonus 20', 'deposit bonus 10'],
    'tr': ['kripto/bay bonus 20', 'yatırım bonusu 10']
}

def format_number(n):
    n_ceil = math.ceil(n)
    return f"{n_ceil:,}".replace(",", " ")

async def send_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [['Русский', 'English', 'Türkçe']]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(MESSAGES['enter_language']['ru'], reply_markup=reply_markup)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_language[user_id] = user_language.get(user_id, 'ru')  # По умолчанию русский

    if not user_authenticated.get(user_id):
        # При первом запуске — показать выбор языка
        await send_language_selection(update, context)
        return

    user_active_status[user_id] = True
    user_spam_status[user_id] = True
    user_count_calc[user_id] = 0
    lang = user_language.get(user_id, 'ru')

    keyboard = ReplyKeyboardMarkup(keyboards[lang], resize_keyboard=True)
    await update.message.reply_text(MESSAGES['bot_activated'][lang], reply_markup=keyboard)

async def change_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.lower()

    lang_map = {
        'русский': 'ru',
        'russian': 'ru',
        'english': 'en',
        'английский': 'en',
        'turkish': 'tr',
        'türkçe': 'tr'
    }

    if text in lang_map:
        user_language[user_id] = lang_map[text]
        lang = lang_map[text]
        await update.message.reply_text(MESSAGES['language_changed'][lang])

        # После смены языка предложить выбрать бонусы
        keyboard = ReplyKeyboardMarkup(keyboards[lang], resize_keyboard=True)
        await update.message.reply_text(MESSAGES['bot_activated'][lang], reply_markup=keyboard)
    else:
        # Если не язык, передать дальше на обработку
        await handle_message(update, context)

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = user_language.get(user_id, 'ru')
    if not user_authenticated.get(user_id):
        await update.message.reply_text(MESSAGES['password_prompt'][lang] + " Напиши /start.")
        return

    is_active = user_active_status.get(user_id, True)
    msg = "Бот сейчас активен." if is_active else "Бот сейчас остановлен. Напиши /start чтобы включить."
    if lang == 'en':
        msg = "Bot is currently active." if is_active else "Bot is stopped now. Type /start to enable."
    elif lang == 'tr':
        msg = "Bot şu anda aktif." if is_active else "Bot şu anda durduruldu. Başlatmak için /start yazın."

    await update.message.reply_text(msg)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text_raw = update.message.text.strip()
    text = text_raw.lower()
    lang = user_language.get(user_id, 'ru')

    # Если пользователь не выбрал язык и не авторизовался, ждем язык или пароль
    if user_id not in user_language:
        # Выбираем язык, если он еще не выбран
        lang_map = {'русский': 'ru', 'russian': 'ru', 'english': 'en', 'английский': 'en', 'turkish': 'tr', 'türkçe': 'tr'}
        if text in lang_map:
            user_language[user_id] = lang_map[text]
            lang = user_language[user_id]
            await update.message.reply_text(MESSAGES['language_changed'][lang])
            keyboard = ReplyKeyboardMarkup(keyboards[lang], resize_keyboard=True)
            await update.message.reply_text(MESSAGES['bot_activated'][lang], reply_markup=keyboard)
        else:
            await send_language_selection(update, context)
        return

    if not user_authenticated.get(user_id):
        if text_raw == PASSWORD:
            user_authenticated[user_id] = True
            user_active_status[user_id] = True
            user_spam_status[user_id] = True
            user_count_calc[user_id] = 0
            keyboard = ReplyKeyboardMarkup(keyboards[lang], resize_keyboard=True)
            await update.message.reply_text(MESSAGES['access_granted'][lang], reply_markup=keyboard)
        else:
            await update.message.reply_text(MESSAGES['password_wrong'][lang])
        return

    if not user_active_status.get(user_id, True):
        return

    # Команды управления
    if text == "stop":
        user_active_status[user_id] = False
        await update.message.reply_text(MESSAGES['stop_message'][lang])
        return

    if text == "stopspam":
        user_spam_status[user_id] = False
        await update.message.reply_text(MESSAGES['stopspam_message'][lang])
        return

    # Проверка выбора бонуса (учитываем язык)
    bonuses = [b.lower() for b in keyboards[lang]]
    bonuses_flat = [item for sublist in bonuses for item in (sublist if isinstance(sublist, list) else [sublist])]

    if text in bonuses_flat:
        user_choice_data[user_id] = text
        await update.message.reply_text(f"{text_raw} {MESSAGES['enter_amount'][lang] if 'enter_amount' in MESSAGES else 'Теперь введи сумму.'}")
        return

    if user_id in user_choice_data:
        choice = user_choice_data[user_id]
        try:
            sums = [float(s.replace(',', '.')) for s in text_raw.split()]
        except ValueError:
            await update.message.reply_text({
                'ru': "Пожалуйста, введи корректное число или числа.",
                'en': "Please enter a valid number or numbers.",
                'tr': "Lütfen geçerli bir sayı veya sayılar girin."
            }[lang])
            return

        is_plural = len(sums) > 1

        intro = (
            {
                'ru': "Для выполнения условий отыгрыша с вашими суммами бонуса потребуется сделать следующие объёмы ставок в разных играх:\n",
                'en': "To meet the wagering conditions, you need to:\n",
                'tr': "Çevrim şartlarını karşılamak için ihtiyacınız olan bahis miktarları:\n"
            }[lang] if is_plural else
            {
                'ru': "Для выполнения условий отыгрыша с вашей суммой бонуса потребуется сделать следующие объёмы ставок в разных играх:\n",
                'en': "To meet the wagering conditions, you need to:\n",
                'tr': "Çevrim şartlarını karşılamak için ihtiyacınız olan bahis miktarları:\n"
            }[lang]
        )

        amount_label = {
            'ru': 'Сумма',
            'en': 'Amount',
            'tr': 'Tutar'
        }[lang]

        other_games_label = {
            'ru': 'Остальные настольные, crash игры и лайв-казино игры (10%) — отыграть',
            'en': 'Other games (10%) —',
            'tr': 'Diğer oyunlar (10%) —'
        }[lang]

        results = []

        for num in sums:
            # Определяем какой бонус выбран, сопоставляя с названием на языке пользователя
            if choice == BONUSES[lang][0].lower():
                sums2 = num * 0.20
                sums3 = sums2 * 20
            elif choice == BONUSES[lang][1].lower():
                sums2 = num * 0.10
                sums3 = sums2 * 15
            else:
                # Если не совпало, пробуем найти совпадение по всем языкам (на случай ошибки)
                if choice in [b.lower() for b in BONUSES['ru']]:
                    if choice == BONUSES['ru'][0].lower():
                        sums2 = num * 0.20
                        sums3 = sums2 * 20
                    else:
                        sums2 = num * 0.10
                        sums3 = sums2 * 15
                elif choice in [b.lower() for b in BONUSES['en']]:
                    if choice == BONUSES['en'][0].lower():
                        sums2 = num * 0.20
                        sums3 = sums2 * 20
                    else:
                        sums2 = num * 0.10
                        sums3 = sums2 * 15
                elif choice in [b.lower() for b in BONUSES['tr']]:
                    if choice == BONUSES['tr'][0].lower():
                        sums2 = num * 0.20
                        sums3 = sums2 * 20
                    else:
                        sums2 = num * 0.10
                        sums3 = sums2 * 15
                else:
                    continue

            slots = sums3 + num
            roulette = sums3 * 3.33 + num
            blackjack = sums3 * 5 + num
            crash = sums3 * 10 + num

            results.append(
                f"{amount_label}: {format_number(num)} som\n"
                f"🔹 Slots (100%) — {format_number(slots)} som\n"
                f"🔹 Roulette (30%) — {format_number(roulette)} som\n"
                f"🔹 Blackjack (20%) — {format_number(blackjack)} som\n"
                f"🔹 {other_games_label} {format_number(crash)} som"
            )

        result_text = intro + "\n\n".join(results)
        await update.message.reply_text(result_text)

        user_count_calc[user_id] = user_count_calc.get(user_id, 0) + 1
        count = user_count_calc[user_id]

        if user_spam_status.get(user_id, True):
            await update.message.reply_text(MESSAGES['calc_warning'][lang])
        else:
            if count % 10 == 0:
                await update.message.reply_text(MESSAGES['calc_warning_10'][lang])
    else:
        keyboard = ReplyKeyboardMarkup(keyboards[lang], resize_keyboard=True)
        await update.message.reply_text(MESSAGES['choose_bonus'][lang], reply_markup=keyboard)


if __name__ == '__main__':
    app = ApplicationBuilder().token(os.environ.get("BOT_TOKEN")).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('status', status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, change_language))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()
