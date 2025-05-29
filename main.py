from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import os
import math
import unicodedata

user_choice_data = {}
user_active_status = {}
user_spam_status = {}
user_count_calc = {}
user_authenticated = {}
user_language = {}

PASSWORD = "starzbot"

LANGUAGES = {
    "ru": "Русский",
    "en": "English",
    "tr": "Türkçe"
}

# Кнопки бонусов по языкам
BONUSES = {
    "ru": ['Крипто/Бай бонус 20', 'Депозит бонус 10'],
    "en": ['Crypto/Buy bonus 20', 'Deposit bonus 10'],
    "tr": ['Kripto/Bayi bonusu 20', 'Mevduat bonusu 10']
}

def format_number(n):
    n_ceil = math.ceil(n)
    # Везде пробел как разделитель тысяч
    return f"{n_ceil:,}".replace(",", " ")

def get_bonus_keyboard(lang):
    return ReplyKeyboardMarkup([[b] for b in BONUSES.get(lang, BONUSES['ru'])], resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Установка языка по умолчанию при старте
    if user_id not in user_language:
        user_language[user_id] = 'ru'

    if not user_authenticated.get(user_id):
        await update.message.reply_text({
            'ru': "Введите пароль для доступа к боту:",
            'en': "Enter password to access the bot:",
            'tr': "Bota erişim için şifreyi girin:"
        }[user_language[user_id]])
        return

    user_active_status[user_id] = True
    user_spam_status[user_id] = True
    user_count_calc[user_id] = 0

    await update.message.reply_text({
        'ru': "Бот активирован. Выбери бонус для расчёта и введи сумму:",
        'en': "Bot activated. Choose a bonus to calculate and enter the amount:",
        'tr': "Bot etkinleştirildi. Hesaplamak için bir bonus seçin ve tutarı girin:"
    }[user_language[user_id]], reply_markup=get_bonus_keyboard(user_language[user_id]))

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = user_language.get(user_id, 'ru')

    if not user_authenticated.get(user_id):
        await update.message.reply_text({
            'ru': "Сначала введите пароль. Напиши /start.",
            'en': "Please enter the password first. Type /start.",
            'tr': "Önce şifreyi girin. /start yazın."
        }[lang])
        return

    is_active = user_active_status.get(user_id, True)
    await update.message.reply_text({
        'ru': "Бот сейчас активен." if is_active else "Бот сейчас остановлен. Напиши /start чтобы включить.",
        'en': "The bot is active now." if is_active else "The bot is stopped now. Type /start to activate.",
        'tr': "Bot şu anda aktif." if is_active else "Bot şu anda durduruldu. Yeniden başlatmak için /start yazın."
    }[lang])

async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Клавиатура выбора языка
    keyboard = ReplyKeyboardMarkup([[v] for v in LANGUAGES.values()], resize_keyboard=True)
    await update.message.reply_text(
        "Пожалуйста, выберите язык / Please select a language / Lütfen bir dil seçin:",
        reply_markup=keyboard
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    lang = user_language.get(user_id, 'ru')

    # Если пользователь выбирает язык из клавиатуры
    if text in LANGUAGES.values():
        # Сопоставляем название языка с ключом
        for key, val in LANGUAGES.items():
            if val == text:
                user_language[user_id] = key
                lang = key
                break
        user_choice_data.pop(user_id, None)  # сброс выбора бонуса
        await update.message.reply_text({
            'ru': "Язык установлен на русский.",
            'en': "Language set to English.",
            'tr': "Dil Türkçe olarak ayarlandı."
        }[lang], reply_markup=get_bonus_keyboard(lang))
        return

    # Если пользователь ещё не авторизован по паролю
    if not user_authenticated.get(user_id):
        if text == PASSWORD:
            user_authenticated[user_id] = True
            user_active_status[user_id] = True
            user_spam_status[user_id] = True
            user_count_calc[user_id] = 0
            await update.message.reply_text({
                'ru': "Доступ разрешён! Выбери бонус и введи сумму:",
                'en': "Access granted! Choose a bonus and enter the amount:",
                'tr': "Erişim sağlandı! Bir bonus seçin ve tutarı girin:"
            }[lang], reply_markup=get_bonus_keyboard(lang))
        else:
            await update.message.reply_text({
                'ru': "Неверный пароль. Повторите попытку.",
                'en': "Wrong password. Please try again.",
                'tr': "Yanlış şifre. Lütfen tekrar deneyin."
            }[lang])
        return

    if not user_active_status.get(user_id, True):
        return

    # Команды стоп
    if text.lower() == "stop":
        user_active_status[user_id] = False
        await update.message.reply_text({
            'ru': "Бот остановлен. Чтобы запустить снова, напиши /start.",
            'en': "Bot stopped. To start again, type /start.",
            'tr': "Bot durduruldu. Yeniden başlatmak için /start yazın."
        }[lang])
        return

    if text.lower() == "stopspam":
        user_spam_status[user_id] = False
        await update.message.reply_text({
            'ru': "Предупреждения больше показываться не будут, кроме каждых 10 подсчётов.",
            'en': "Warnings will no longer appear except every 10 calculations.",
            'tr': "Uyarılar artık gösterilmeyecek, sadece her 10 hesaplamada bir."
        }[lang])
        return

    # Проверяем выбор бонуса по языку
    bonuses_lower = [b.lower() for b in BONUSES[lang]]
    text_lower = text.lower()

    if text_lower in bonuses_lower:
        # Сохраняем выбор бонуса (оригинальный текст, чтобы потом использовать)
        index = bonuses_lower.index(text_lower)
        user_choice_data[user_id] = BONUSES[lang][index].lower()
        await update.message.reply_text({
            'ru': f"Выбран: {BONUSES[lang][index]}. Теперь введи сумму.",
            'en': f"Selected: {BONUSES[lang][index]}. Now enter the amount.",
            'tr': f"Seçildi: {BONUSES[lang][index]}. Şimdi tutarı girin."
        }[lang])
        return

    # Если бонус уже выбран, обрабатываем ввод суммы
    if user_id in user_choice_data:
        choice = user_choice_data[user_id]

        try:
            sums = [float(s.replace(',', '.')) for s in text.split()]
        except ValueError:
            await update.message.reply_text({
                'ru': "Пожалуйста, введи корректное число или числа.",
                'en': "Please enter a valid number or numbers.",
                'tr': "Lütfen geçerli bir sayı veya sayılar girin."
            }[lang])
            return

        is_plural = len(sums) > 1
        results = []

        for num in sums:
            if choice == BONUSES['ru'][0].lower() or choice == BONUSES['en'][0].lower() or choice == BONUSES['tr'][0].lower():
                sums2 = num * 0.20
                sums3 = sums2 * 20
            elif choice == BONUSES['ru'][1].lower() or choice == BONUSES['en'][1].lower() or choice == BONUSES['tr'][1].lower():
                sums2 = num * 0.10
                sums3 = sums2 * 15
            else:
                continue

            slots = sums3 + num
            roulette = sums3 * 3.33 + num
            blackjack = sums3 * 5 + num
            crash = sums3 * 10 + num

            results.append(
                f"{{
                    'ru': 'Сумма',
                    'en': 'Amount',
                    'tr': 'Tutar'
                }[lang]}: {format_number(num)} som\n"
                f"🔹 Slots (100%) — {format_number(slots)} som\n"
                f"🔹 Roulette (30%) — {format_number(roulette)} som\n"
                f"🔹 Blackjack (20%) — {format_number(blackjack)} som\n"
                f"🔹 {{
                    'ru': 'Остальные настольные, crash игры и лайв-казино игры (10%) — отыграть',
                    'en': 'Other games (10%) —',
                    'tr': 'Diğer oyunlar (10%) —'
                }[lang]} {format_number(crash)} som"
            )

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

        result_text = intro + "\n\n".join(results)
        await update.message.reply_text(result_text)

        user_count_calc[user_id] = user_count_calc.get(user_id, 0) + 1
        count = user_count_calc[user_id]

        if user_spam_status.get(user_id, True):
            await update.message.reply_text({
                'ru': "Обязательно перепроверяйте итоговые суммы! Это для вашей же страховки. Если хотите, чтобы это сообщение больше не появлялось, напишите stopspam.",
                'en': "Please double-check the final amounts! This is for your own safety. If you want to stop this message, type stopspam.",
                'tr': "Lütfen son tutarları kontrol edin! Bu sizin güvenliğiniz için. Bu mesajı görmek istemiyorsanız, stopspam yazın."
            }[lang])
        else:
            if count % 10 == 0:
                await update.message.reply_text({
                    'ru': "Обязательно перепроверяйте итоговые суммы! Это для вашей же страховки.",
                    'en': "Please double-check the final amounts! This is for your own safety.",
                    'tr': "Lütfen son tutarları kontrol edin! Bu sizin güvenliğiniz için."
                }[lang])
    else:
        await update.message.reply_text({
            'ru': "Сначала выбери бонус кнопкой ниже.",
            'en': "Please select a bonus using the buttons below first.",
            'tr': "Lütfen önce aşağıdaki düğmelerden bir bonus seçin."
        }[lang], reply_markup=get_bonus_keyboard(lang))

if __name__ == '__main__':
    app = ApplicationBuilder().token(os.environ.get("BOT_TOKEN")).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('status', status))
    app.add_handler(CommandHandler('language', language_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()
