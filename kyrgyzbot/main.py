import os
import random
import logging

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    ConversationHandler, ContextTypes
)

from states import CHOOSING_MODE, WORD_QUIZ, NUMBER_QUIZ
from words import get_random_word_question, check_word_answer
from numbers import get_number_question, check_number_answer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Команды ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_keyboard = [["Слова", "Цифры"]]
    await update.message.reply_text(
        "Привет! Выбери режим:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True),
    )
    return CHOOSING_MODE

# --- Режим Слова ---

async def word_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "word"
    return await ask_word_question(update, context)

async def ask_word_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question, answer = get_random_word_question()
    context.user_data["current_answer"] = answer
    await update.message.reply_text(f"Переведи: {question}")
    return WORD_QUIZ

async def word_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip().lower()
    correct = check_word_answer(user_input, context.user_data["current_answer"])
    if correct:
        await update.message.reply_text("✅ Верно!\nСледующий вопрос:")
        return await ask_word_question(update, context)
    else:
        await update.message.reply_text("❌ Неверно. Попробуй ещё раз:")
        return WORD_QUIZ

# --- Режим Цифры ---

async def number_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "number"
    return await ask_number_question(update, context)

async def ask_number_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question_type = random.choice(["digit_to_text", "text_to_digit"])
    number, question = get_number_question(question_type)
    context.user_data["current_number"] = number
    context.user_data["question_type"] = question_type
    await update.message.reply_text(f"Напиши: {question}")
    return NUMBER_QUIZ

async def number_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip().lower()
    correct = check_number_answer(user_input, context.user_data["current_number"], context.user_data["question_type"])
    if correct:
        await update.message.reply_text("✅ Верно!\nСледующий вопрос:")
        return await ask_number_question(update, context)
    else:
        await update.message.reply_text("❌ Неверно. Попробуй ещё раз:")
        return NUMBER_QUIZ

# --- Отмена ---

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Завершено!", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# === Основная функция запуска ===

def main():
    token = os.getenv("KGZ_TOKEN")
    if not token:
        logger.error("Ошибка: Не найден токен KGZ_TOKEN в переменных окружения!")
        return

    app = ApplicationBuilder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_MODE: [
                MessageHandler(filters.Regex("^Слова$"), word_mode),
                MessageHandler(filters.Regex("^Цифры$"), number_mode),
            ],
            WORD_QUIZ: [MessageHandler(filters.TEXT & ~filters.COMMAND, word_answer)],
            NUMBER_QUIZ: [MessageHandler(filters.TEXT & ~filters.COMMAND, number_answer)],
        },
        fallbacks=[CommandHandler("stop", cancel)],
    )

    app.add_handler(conv_handler)

    logger.info("Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()

