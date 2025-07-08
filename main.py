import logging
import sqlite3
import json
import os
import random

from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    MessageHandler, filters, ConversationHandler
)

import openai
from prompts import TRAINING_PROMPT  # импорт промпта из prompts.py

# === CONFIG ===
BOT_TOKEN = os.environ["BOT_TOKEN"]
API_KEY = os.environ["OPENAI_KEY"]
openai.api_key = API_KEY

DB_FILE = "data.db"
SCENARIO_FILE = "scenarios.json"
RULES_FOLDER = "rules"
PASSWORD = "starzbot"

# === STATES ===
AUTH, LOGIN, PASSWORD_STATE, AWAITING_ANSWER = range(4)

# === LOGGER ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === SESSION ===
session = {}

# === DATABASE INIT ===
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            login TEXT,
            password TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            question TEXT,
            answer TEXT,
            evaluation TEXT,
            grammar_issues TEXT,
            correct_answer TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS error_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            question TEXT,
            answer TEXT,
            evaluation TEXT
        )
    ''')
    conn.commit()
    conn.close()

# === LOAD SCENARIOS ===
def load_scenarios():
    with open(SCENARIO_FILE, encoding='utf-8') as f:
        data = json.load(f)
    random.shuffle(data)
    return data

# === OPENAI EVALUATION ===
async def evaluate_answer(entry, user_answer):
    """
    Формируем полный промпт из TRAINING_PROMPT, подставляя вопрос и эталонный ответ.
    Добавляем ответ оператора в конец, отправляем на оценку.
    """
    question = entry["question"]
    expected_answer = entry["expected_answer"]

    # Формируем промпт, подставляя question и expected_answer
    prompt = TRAINING_PROMPT.format(question=question, expected_answer=expected_answer)
    # Добавляем ответ оператора для оценки
    prompt += f"\n\nОтвет оператора:\n{user_answer}"

    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Ты — ассистент для оценки ответов операторов."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0
        )
        content = response["choices"][0]["message"]["content"].strip()

        # Попытка выделить ключевые оценки из текста (если нужно можно усложнить парсинг)
        # Для простоты, возвращаем просто весь текст оценки
        return {
            "evaluation_text": content,
            "evaluation_simple": None  # Можно позже доработать парсер оценки
        }
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        return {
            "evaluation_text": "Ошибка при оценке ИИ. Попробуйте позже.",
            "evaluation_simple": "incorrect"
        }

# === AUTH FLOW ===
async def auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите логин:")
    return LOGIN

async def login_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["login"] = update.message.text.strip()
    await update.message.reply_text("Введите пароль:")
    return PASSWORD_STATE

async def password_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip()
    user_id = update.effective_user.id
    login = context.user_data.get("login")
    username = update.effective_user.username

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    existing = c.fetchone()

    if existing:
        c.execute("SELECT * FROM users WHERE user_id=? AND password=?", (user_id, password))
        if c.fetchone():
            session[user_id] = {"authenticated": True}
            await update.message.reply_text("Успешный вход. Напишите /start для начала.")
        else:
            await update.message.reply_text("Неверный пароль. Попробуйте снова через /auth.")
    else:
        c.execute("INSERT INTO users (user_id, username, login, password) VALUES (?, ?, ?, ?)",
                  (user_id, username, login, password))
        session[user_id] = {"authenticated": True}
        await update.message.reply_text("Регистрация успешна. Напишите /start для начала.")
    conn.commit()
    conn.close()
    return ConversationHandler.END

# === TRAINING FLOW ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in session or not session[user_id].get("authenticated"):
        await update.message.reply_text("Сначала авторизуйтесь через /auth.")
        return ConversationHandler.END

    scenario = load_scenarios()
    session[user_id]["scenario"] = scenario
    session[user_id]["step"] = 0
    session[user_id]["score"] = {"correct": 0, "partial": 0, "incorrect": 0}

    await ask_next(update, context)
    return AWAITING_ANSWER

async def ask_next(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    step = session[user_id]["step"]
    scenario = session[user_id]["scenario"]

    if step >= len(scenario):
        await update.message.reply_text("✅ Тренировка завершена. Команда /stop — статистика.")
        return ConversationHandler.END

    current = scenario[step]
    session[user_id]["current"] = current
    await update.message.reply_text(f"Вопрос: {current['question']}")

async def process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in session or "current" not in session[user_id]:
        await update.message.reply_text("Сначала напишите /start.")
        return

    answer = update.message.text.strip()
    entry = session[user_id]["current"]

    # Обработка команды /answer
    if answer.lower() == "/answer":
        await update.message.reply_text(f"Правильный ответ:\n{entry['expected_answer']}")
        return

    # Оценка ИИ
    result = await evaluate_answer(entry, answer)
    evaluation_text = result["evaluation_text"]

    # Запись лога и подсчёт (упрощённо: ищем ключевые слова в тексте оценки)
    evaluation_simple = None
    if "полностью верно" in evaluation_text.lower() or "✅" in evaluation_text:
        evaluation_simple = "correct"
    elif "частично верно" in evaluation_text.lower() or "⚠️" in evaluation_text:
        evaluation_simple = "partial"
    else:
        evaluation_simple = "incorrect"

    # Запоминаем последний ответ и оценку
    session[user_id]["last"] = {
        "question": entry["question"],
        "answer": answer,
        "evaluation": evaluation_simple,
        "correct_answer": entry["expected_answer"]
    }

    # Записываем в базу
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        INSERT INTO logs (user_id, question, answer, evaluation, grammar_issues, correct_answer)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, entry["question"], answer, evaluation_simple, "", entry["expected_answer"]))
    conn.commit()
    conn.close()

    # Обновляем счёт
    session[user_id]["score"][evaluation_simple] += 1

    # Ответ пользователю по оценке
    if evaluation_simple == "correct":
        await update.message.reply_text(f"✅ Верно!\n\nКомментарий ИИ:\n{evaluation_text}")
        session[user_id]["step"] += 1
        await ask_next(update, context)
    elif evaluation_simple == "partial":
        await update.message.reply_text(f"🟡 Почти правильно.\n\nКомментарий ИИ:\n{evaluation_text}")
    else:
        await update.message.reply_text(f"❌ Не совсем.\n\nКомментарий ИИ:\n{evaluation_text}")

async def show_correct(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    last = session.get(user_id, {}).get("last")
    if not last:
        await update.message.reply_text("Нет ответа для показа.")
        return
    await update.message.reply_text(f"Правильный ответ:\n{last['correct_answer']}")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    score = session.get(user_id, {}).get("score", {"correct":0,"partial":0,"incorrect":0})
    msg = (f"📊 Статистика:\n"
           f"✅ Верных: {score.get('correct', 0)}\n"
           f"🟡 Частично: {score.get('partial', 0)}\n"
           f"❌ Неверных: {score.get('incorrect', 0)}")
    await update.message.reply_text(msg)

async def report_error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    last = session.get(user_id, {}).get("last")
    if not last:
        await update.message.reply_text("Нет жалобы для отправки.")
        return

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO error_reports (user_id, question, answer, evaluation) VALUES (?, ?, ?, ?)",
              (user_id, last["question"], last["answer"], last["evaluation"]))
    conn.commit()
    conn.close()
    await update.message.reply_text("Жалоба отправлена.")

# === MAIN ===
if __name__ == '__main__':
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    auth_conv = ConversationHandler(
        entry_points=[CommandHandler("auth", auth)],
        states={
            LOGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_input)],
            PASSWORD_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, password_input)],
        },
        fallbacks=[],
    )
    app.add_handler(auth_conv)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("answer", show_correct))
    app.add_handler(CommandHandler("error", report_error))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process))

    app.run_polling()
