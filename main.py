from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import os
import math
import sys

user_choice_data = {}
user_active_status = {}
user_spam_status = {}
user_count_calc = {}
user_authenticated = {}
user_language = {}
user_waiting_for_password = set()
user_waiting_for_language = set()

PASSWORD = "starzbot"

# Клавиатура бонусов для каждого языка
keyboards = {
    'ru': [['Крипто/Бай бонус 20'], ['Депозит бонус 10']],
    'en': [['Crypto/Buy Bonus 20'], ['Deposit Bonus 10']],
    'tr': [['Kripto/Bay Bonus 20'], ['Depozito Bonus 10']],
}

markup_by_lang = {
    lang: ReplyKeyboardMarkup(keyboards[lang], resize_keyboard=True)
    for lang in keyboards
}

language_keyboard = ReplyKeyboardMarkup(
    [['Русский', 'English', 'Türkçe']],
    resize_keyboard=True,
    one_time_keyboard=True
)

def format_number(n):
    n_ceil = math.ceil(n)
    return f"{n_ceil:,}".replace(",", " ")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_language[user_id] = 'ru'  # по умолчанию русский
    user_authenticated[user_id] = False
    user_active_status[user_id] = False
    user_choice_data.pop(user_id, None)
    user_count_calc[user_id] = 0
    user_spam_status[user_id] = True
    user_waiting_for_password.add(user_id)

    await update.message.reply_text(
        "Выберите язык / Please choose a language / Lütfen bir dil seçin:",
        reply_markup=language_keyboard
    )

async def change_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_waiting_for_language.add(user_id)
    await update.message.reply_text(
        "Пожалуйста, выберите язык:\nPlease choose language:\nLütfen bir dil seçin:",
        reply_markup=language_keyboard
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = user_language.get(user_id, 'ru')

    if not user_authenticated.get(user_id):
        texts = {
            'ru': "Сначала введите пароль. Напиши /start.",
            'en': "Please enter the password first. Use /start.",
            'tr': "Lütfen önce şifreyi girin. /start komutunu kullanın."
        }
        await update.message.reply_text(texts[lang])
        return

    is_active = user_active_status.get(user_id, True)
    texts_active = {
        'ru': "Бот сейчас активен.",
        'en': "Bot is currently active.",
        'tr': "Bot şu anda aktif."
    }
    texts_inactive = {
        'ru': "Бот сейчас остановлен. Напиши /start чтобы включить.",
        'en': "Bot is stopped now. Use /start to activate.",
        'tr': "Bot şu anda durduruldu. Etkinleştirmek için /start yazın."
    }
    await update.message.reply_text(texts_active[lang] if is_active else texts_inactive[lang])

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # Проверяем выбор языка, если ждем
    if user_id in user_waiting_for_language:
        chosen_lang = None
        if text.lower() in ['русский', 'ru', 'russian']:
            chosen_lang = 'ru'
        elif text.lower() in ['english', 'английский', 'en']:
            chosen_lang = 'en'
        elif text.lower() in ['türkçe', 'turkish', 'tr']:
            chosen_lang = 'tr'

        if chosen_lang:
            user_language[user_id] = chosen_lang
            user_waiting_for_language.remove(user_id)
            user_waiting_for_password.add(user_id)
            texts = {
                'ru': "Язык выбран: Русский.\nТеперь введите пароль:",
                'en': "Language set to English.\nPlease enter the password:",
                'tr': "Dil Türkçe olarak seçildi.\nLütfen şifreyi girin:"
            }
            await update.message.reply_text(texts[chosen_lang], reply_markup=ReplyKeyboardRemove())
        else:
            await update.message.reply_text(
                "Неверный выбор языка. Пожалуйста, выберите из кнопок.",
                reply_markup=language_keyboard
            )
        return

    # Проверка пароля, если ждем пароль
    if user_id in user_waiting_for_password:
        if text == PASSWORD:
            user_authenticated[user_id] = True
            user_active_status[user_id] = True
            user_spam_status[user_id] = True
            user_count_calc[user_id] = 0
            user_waiting_for_password.remove(user_id)
            lang = user_language.get(user_id, 'ru')
            await update.message.reply_text(
                {
                    'ru': "Доступ разрешён! Выбери бонус и введи сумму:",
                    'en': "Access granted! Choose a bonus and enter the amount:",
                    'tr': "Erişim onaylandı! Bonus seçin ve miktarı girin:"
                }[lang],
                reply_markup=markup_by_lang[lang]
            )
        else:
            lang = user_language.get(user_id, 'ru')
            await update.message.reply_text(
                {
                    'ru': "Неверный пароль. Повторите попытку.",
                    'en': "Incorrect password. Please try again.",
                    'tr': "Yanlış şifre. Lütfen tekrar deneyin."
                }[lang]
            )
        return

    lang = user_language.get(user_id, 'ru')

    # Обработка команды /lang
    if text.lower() == '/lang':
        await change_language(update, context)
        return

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

    # Обработка команд стоп
    if text.lower() == "stop":
        user_active_status[user_id] = False
        await update.message.reply_text(
            {
                'ru': "Бот остановлен. Чтобы запустить снова, напиши /start.",
                'en': "Bot stopped. To start again, type /start.",
                'tr': "Bot durduruldu. Yeniden başlatmak için /start yazın."
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

    # Проверка выбора бонуса
    bonuses_lower = [b[0].lower() for b in keyboards[lang]]
    if text.lower() in bonuses_lower:
        user_choice_data[user_id] = text.lower()
        await update.message.reply_text(
            {
                'ru': f"Выбран: {text}. Теперь введи сумму.",
                'en': f"Selected: {text}. Now enter the amount.",
                'tr': f"Seçildi: {text}. Şimdi miktarı girin."
            }[lang]
        )
        return

    if user_id not in user_choice_data:
        await update.message.reply_text(
            {
                'ru': "Сначала выбери бонус кнопкой ниже.",
                'en': "First select a bonus using the buttons below.",
                'tr': "Önce aşağıdaki düğmelerden bir bonus seçin."
            }[lang],
            reply_markup=markup_by_lang[lang]
        )
        return

    # Обработка числового ввода суммы
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

    choice = user_choice_data[user_id]
    results = []
    for num in sums:
        if lang == 'ru':
            if 'депозит' in choice:
                sums2 = num * 0.10
                sums3 = sums2 * 15
            elif 'крипто' in choice or 'бай' in choice:
                sums2 = num * 0.20
                sums3 = sums2 * 20
            else:
                sums2 = sums3 = 0
        else:
            choice_en = choice.lower()
            if 'deposit' in choice_en or 'депозит' in choice_en:
                sums2 = num * 0.10
                sums3 = sums2 * 15
            elif 'crypto' in choice_en or 'buy' in choice_en or 'крипто' in choice_en or 'бай' in choice_en:
                sums2 = num * 0.20
                sums3 = sums2 * 20
            else:
                sums2 = sums3 = 0

        res_text = f"{format_number(num)} -> {format_number(sums2)} -> {format_number(sums3)}"
        results.append(res_text)

    await update.message.reply_text("\n".join(results))

if __name__ == '__main__':
    TOKEN = os.getenv("BOT_TOKEN")
    if not TOKEN:
        print("Ошибка: Не задан токен бота. Установите переменную окружения BOT_TOKEN.")
        sys.exit(1)

    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Бот запущен...")
    application.run_polling()
