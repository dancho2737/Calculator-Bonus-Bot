# -*- coding: utf-8 -*-
import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters, ConversationHandler
)

LANG, PASSWORD, BONUS, AMOUNT = range(4)

PASSWORD_CORRECT = "starzbot"

messages = {
    'ru': {
        'choose_lang': "Выберите язык / Select language / Dil seçin:\n1. Русский\n2. English\n3. Türkçe",
        'ask_password': "Введите пароль:",
        'wrong_password': "Неверный пароль, попробуйте снова.",
        'password_ok': "Пароль принят. Выберите бонус:\n1. Бай бонус 20%\n2. Крипто бонус 20%\n3. Депозитный бонус 10%",
        'choose_bonus': "Выберите бонус:\n1. Бай бонус 20%\n2. Крипто бонус 20%\n3. Депозитный бонус 10%",
        'ask_amount': "Введите сумму (или несколько чисел через пробел):",
        'results': """Для выполнения условий отыгрыша с вашей суммой бонуса потребуется сделать следующие объёмы ставок в разных играх:

🔹 Слоты (100%) — отыграть {slots} сомов

🔹 Roulette (30%) — отыграть {roulette} сомов

🔹 Blackjack (20%) — отыграть {blackjack} сомов

🔹 Остальные настольные, crash игры и лайв-казино игры (10%) — отыграть {crash} сомов
""",
        'check_sums_reminder': "Обязательно проверяйте свои итоговые суммы! Это для вашей же страховки.",
        'stopspam_enabled': "Сообщение с напоминанием отключено.",
        'stopspam_disabled': "Сообщение с напоминанием включено.",
        'stopspam_prompt': "Для включения/отключения напоминаний используйте команду /stopspam",
    },
    'en': {
        'choose_lang': "Choose language / Dil seçin:\n1. Russian\n2. English\n3. Turkish",
        'ask_password': "Enter password:",
        'wrong_password': "Wrong password, try again.",
        'password_ok': "Password accepted. Choose a bonus:\n1. Buy Bonus 20%\n2. Crypto Bonus 20%\n3. Deposit Bonus 10%",
        'choose_bonus': "Choose a bonus:\n1. Buy Bonus 20%\n2. Crypto Bonus 20%\n3. Deposit Bonus 10%",
        'ask_amount': "Enter amount (or multiple numbers separated by space):",
        'results': """To meet the wagering requirements with your bonus amount, you will need to make the following bet volumes in different games:

🔹 Slots (100%) — wager {slots}

🔹 Roulette (30%) — wager {roulette}

🔹 Blackjack (20%) — wager {blackjack}

🔹 Other table, crash and live casino games (10%) — wager {crash}
""",
        'check_sums_reminder': "Please double-check your final sums! This is for your own protection.",
        'stopspam_enabled': "Reminder message disabled.",
        'stopspam_disabled': "Reminder message enabled.",
        'stopspam_prompt': "Use /stopspam to toggle reminders on/off",
    },
    'tr': {
        'choose_lang': "Dil seçin / Choose language / Выберите язык:\n1. Rusça\n2. İngilizce\n3. Türkçe",
        'ask_password': "Şifreyi girin:",
        'wrong_password': "Yanlış şifre, tekrar deneyin.",
        'password_ok': "Şifre kabul edildi. Bonus seçin:\n1. Bay Bonus %20\n2. Kripto Bonus %20\n3. Depozito Bonusu %10",
        'choose_bonus': "Bonus seçin:\n1. Bay Bonus %20\n2. Kripto Bonus %20\n3. Depozito Bonusu %10",
        'ask_amount': "Tutar girin (veya boşlukla ayrılmış birden fazla sayı):",
        'results': """Bonus tutarınızla çevrim şartlarını yerine getirmek için farklı oyunlarda aşağıdaki bahis hacimlerini yapmanız gerekmektedir:

🔹 Slotlar (100%) — oynanacak {slots}

🔹 Rulet (30%) — oynanacak {roulette}

🔹 Blackjack (20%) — oynanacak {blackjack}

🔹 Diğer masa oyunları, crash ve canlı casino oyunları (10%) — oynanacak {crash}
""",
        'check_sums_reminder': "Lütfen son tutarları mutlaka kontrol edin! Bu sizin güvenliğiniz için.",
        'stopspam_enabled': "Hatırlatma mesajı kapatıldı.",
        'stopspam_disabled': "Hatırlatma mesajı açıldı.",
        'stopspam_prompt': "Hatırlatmaları açıp kapatmak için /stopspam komutunu kullanın",
    }
}

# Для хранения данных пользователя (язык, бонус, стопспам, счетчик)
user_data_store = {}

def get_user_data(user_id):
    if user_id not in user_data_store:
        user_data_store[user_id] = {
            'lang': 'ru',
            'bonus': None,
            'stopspam': False,
            'count': 0,
            'password_ok': False
        }
    return user_data_store[user_id]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = get_user_data(user_id)
    data['password_ok'] = False
    await update.message.reply_text(messages['ru']['choose_lang'])
    return LANG

async def lang_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id
    data = get_user_data(user_id)
    lang_map = {'1': 'ru', '2': 'en', '3': 'tr'}
    if text in lang_map:
        data['lang'] = lang_map[text]
        await update.message.reply_text(messages[data['lang']]['ask_password'])
        return PASSWORD
    else:
        await update.message.reply_text(messages[data['lang']]['choose_lang'])
        return LANG

async def password_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = get_user_data(user_id)
    if update.message.text.strip() == PASSWORD_CORRECT:
        data['password_ok'] = True
        await update.message.reply_text(messages[data['lang']]['password_ok'])
        await update.message.reply_text(messages[data['lang']]['choose_bonus'])
        return BONUS
    else:
        await update.message.reply_text(messages[data['lang']]['wrong_password'])
        return PASSWORD

async def bonus_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id
    data = get_user_data(user_id)
    if text == '1':
        data['bonus'] = 'buy_crypto'  # 20%
    elif text == '2':
        data['bonus'] = 'buy_crypto'  # 20%
    elif text == '3':
        data['bonus'] = 'deposit'     # 10%
    else:
        await update.message.reply_text(messages[data['lang']]['choose_bonus'])
        return BONUS
    await update.message.reply_text(messages[data['lang']]['ask_amount'])
    return AMOUNT

def calculate_amounts(bonus_type, nums):
    results = []
    for num in nums:
        if bonus_type == 'deposit':
            sums2 = num * 0.10
            sums3 = sums2 * 15
        else:  # buy_crypto
            sums2 = num * 0.20
            sums3 = sums2 * 15
        slots = sums3 + num
        roulette = sums3 * 3.33 + num
        blackjack = sums3 * 5 + num
        crash = sums3 * 10 + num
        results.append({
            'slots': int(slots),
            'roulette': int(roulette),
            'blackjack': int(blackjack),
            'crash': int(crash),
            'original': num
        })
    return results

def format_number(n):
    return f"{n:,}".replace(",", " ")

async def amount_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = get_user_data(user_id)
    if not data['password_ok']:
        await update.message.reply_text(messages[data['lang']]['ask_password'])
        return PASSWORD
    text = update.message.text.strip()
    try:
        nums = list(map(int, text.split()))
    except ValueError:
        await update.message.reply_text(messages[data['lang']]['ask_amount'])
        return AMOUNT
    results = calculate_amounts(data['bonus'], nums)
    # Формируем сообщение
    lines = []
    for res in results:
        lines.append(messages[data['lang']]['results'].format(
            slots=format_number(res['slots']),
            roulette=format_number(res['roulette']),
            blackjack=format_number(res['blackjack']),
            crash=format_number(res['crash'])
        ))
    message = "\n".join(lines)
    await update.message.reply_text(message)

    # Напоминание
    if not data['stopspam']:
        data['count'] += 1
        # Каждое сообщение после подсчёта + каждые 7 подсчётов напоминание
        await update.message.reply_text(messages[data['lang']]['check_sums_reminder'])

    return BONUS

async def stopspam_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = get_user_data(user_id)
    data['stopspam'] = not data['stopspam']
    if data['stopspam']:
        await update.message.reply_text(messages[data['lang']]['stopspam_enabled'])
    else:
        await update.message.reply_text(messages[data['lang']]['stopspam_disabled'])

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = get_user_data(user_id)
    await update.message.reply_text(messages[data['lang']]['stopspam_prompt'])

def main():
    TOKEN = os.getenv("TELEGRAM_TOKEN")  # Ваш токен бота
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            LANG: [MessageHandler(filters.TEXT & ~filters.COMMAND, lang_choice)],
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, password_handler)],
            BONUS: [MessageHandler(filters.TEXT & ~filters.COMMAND, bonus_choice)],
            AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, amount_handler)],
        },
        fallbacks=[CommandHandler('stopspam', stopspam_command)]
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler('stopspam', stopspam_command))
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    print("Bot started")
    app.run_polling()

if __name__ == '__main__':
    main()
        
