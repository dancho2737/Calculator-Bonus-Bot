from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup, 
    ReplyKeyboardMarkup, 
    ReplyKeyboardRemove
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters, 
    ContextTypes, CallbackQueryHandler, ConversationHandler
)
import os
import math

# Состояния для ConversationHandler
LANGUAGE, PASSWORD, BONUS_CHOICE, AMOUNT = range(4)

PASSWORD_SECRET = "starzbot"

user_language = {}
user_authenticated = {}

# Клавиатуры выбора языка (ReplyKeyboard)
language_keyboard = ReplyKeyboardMarkup(
    [['Русский', 'English', 'Türkçe']],
    resize_keyboard=True,
    one_time_keyboard=True
)

# Кнопки бонусов (InlineKeyboard) с callback_data
bonus_buttons = {
    'ru': [
        [InlineKeyboardButton("Крипто/Бай Бонус 20%", callback_data="bonus_20")],
        [InlineKeyboardButton("Депозитный Бонус 10%", callback_data="bonus_10")]
    ],
    'en': [
        [InlineKeyboardButton("Crypto/Buy Bonus 20%", callback_data="bonus_20")],
        [InlineKeyboardButton("Deposit Bonus 10%", callback_data="bonus_10")]
    ],
    'tr': [
        [InlineKeyboardButton("Kripto/Bay Bonus 20%", callback_data="bonus_20")],
        [InlineKeyboardButton("Depozito Bonus 10%", callback_data="bonus_10")]
    ]
}

def format_number(n):
    n_ceil = math.ceil(n)
    return f"{n_ceil:,}".replace(",", " ")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_language[user_id] = 'ru'  # по умолчанию русский
    user_authenticated[user_id] = False
    await update.message.reply_text(
        "Выберите язык / Please choose a language / Lütfen bir dil seçin:",
        reply_markup=language_keyboard
    )
    return LANGUAGE

async def language_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.lower()
    lang = None
    if text in ['русский', 'ru', 'russian']:
        lang = 'ru'
    elif text in ['english', 'английский', 'en']:
        lang = 'en'
    elif text in ['türkçe', 'turkish', 'tr']:
        lang = 'tr'
    else:
        await update.message.reply_text("Пожалуйста, выберите язык из предложенных кнопок.", reply_markup=language_keyboard)
        return LANGUAGE
    
    user_language[user_id] = lang
    await update.message.reply_text(
        {
            'ru': "Язык выбран: Русский. Введите пароль:",
            'en': "Language set to English. Please enter password:",
            'tr': "Dil Türkçe olarak seçildi. Lütfen şifreyi girin:"
        }[lang],
        reply_markup=ReplyKeyboardRemove()
    )
    return PASSWORD

async def password_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = user_language.get(user_id, 'ru')
    text = update.message.text.strip()
    if text == PASSWORD_SECRET:
        user_authenticated[user_id] = True
        await update.message.reply_text(
            {
                'ru': "Пароль принят! Выберите бонус:",
                'en': "Password accepted! Choose your bonus:",
                'tr': "Şifre kabul edildi! Bonus seçin:"
            }[lang],
            reply_markup=InlineKeyboardMarkup(bonus_buttons[lang])
        )
        return BONUS_CHOICE
    else:
        await update.message.reply_text(
            {
                'ru': "Неверный пароль. Попробуйте снова:",
                'en': "Wrong password. Try again:",
                'tr': "Yanlış şifre. Tekrar deneyin:"
            }[lang]
        )
        return PASSWORD

async def bonus_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = user_language.get(user_id, 'ru')

    bonus_type = query.data  # bonus_20 или bonus_10
    context.user_data['bonus_type'] = bonus_type

    await query.edit_message_text(
        {
            'ru': "Введите сумму бонуса (в сомах):",
            'en': "Enter the bonus amount (in soms):",
            'tr': "Bonus tutarını girin (som cinsinden):"
        }[lang]
    )
    return AMOUNT

async def amount_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = user_language.get(user_id, 'ru')
    bonus_type = context.user_data.get('bonus_type')
    
    try:
        amount = float(update.message.text.strip().replace(',', '.'))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            {
                'ru': "Пожалуйста, введите корректное положительное число.",
                'en': "Please enter a valid positive number.",
                'tr': "Lütfen geçerli pozitif bir sayı girin."
            }[lang]
        )
        return AMOUNT

    # Расчет
    if bonus_type == "bonus_20":
        bonus_percent = 0.20
        multiplier = 20
    elif bonus_type == "bonus_10":
        bonus_percent = 0.10
        multiplier = 15
    else:
        bonus_percent = 0
        multiplier = 0

    bonus_amount = amount * bonus_percent
    wager = bonus_amount * multiplier
    slots = amount + wager
    roulette = amount + wager * 0.3
    blackjack = amount + wager * 0.2
    others = amount + wager * 0.1

    response = {
        'ru': (
            f"Для выполнения условий отыгрыша с вашим бонусом {format_number(amount)} сом потребуется сделать ставки:\n\n"
            f"🔹 Слоты (100%) — {format_number(slots)} сом\n"
            f"🔹 Рулетка (30%) — {format_number(roulette)} сом\n"
            f"🔹 Блэкджек (20%) — {format_number(blackjack)} сом\n"
            f"🔹 Остальные настольные игры, crash и лайв-казино (10%) — {format_number(others)} сом"
        ),
        'en': (
            f"To meet wagering requirements for your bonus amount {format_number(amount)} soms, you need to wager:\n\n"
            f"🔹 Slots (100%) — {format_number(slots)} soms\n"
            f"🔹 Roulette (30%) — {format_number(roulette)} soms\n"
            f"🔹 Blackjack (20%) — {format_number(blackjack)} soms\n"
            f"🔹 Other table, crash and live casino games (10%) — {format_number(others)} soms"
        ),
        'tr': (
            f"Bonus tutarınız {format_number(amount)} som için çevrim şartlarını karşılamak amacıyla bahis yapmanız gereken tutarlar:\n\n"
            f"🔹 Slotlar (100%) — {format_number(slots)} som\n"
            f"🔹 Rulet (30%) — {format_number(roulette)} som\n"
            f"🔹 Blackjack (20%) — {format_number(blackjack)} som\n"
            f"🔹 Diğer masa oyunları, crash oyunları ve canlı casino (10%) — {format_number(others)} som"
        )
    }

    await update.message.reply_text(response[lang])
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = user_language.get(user_id, 'ru')
    await update.message.reply_text(
        {
            'ru': "Операция отменена.",
            'en': "Operation cancelled.",
            'tr': "İşlem iptal edildi."
        }[lang],
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

if __name__ == "__main__":
    TOKEN = os.getenv("TOKEN")
    if not TOKEN:
        print("Ошибка: не задан токен в переменной окружения TOKEN")
        exit(1)

    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            LANGUAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, language_chosen)],
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, password_entered)],
            BONUS_CHOICE: [CallbackQueryHandler(bonus_chosen)],
            AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, amount_entered)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True
    )

    app.add_handler(conv_handler)

    print("Бот запущен")
    app.run_polling()
