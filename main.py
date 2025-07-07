import logging
import sqlite3
import json
import os
import random

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    MessageHandler, filters, ConversationHandler
)

import openai

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

# === LOAD SCENARIOS & RULES ===
def load_scenarios():
    with open(SCENARIO_FILE, encoding='utf-8') as f:
        data = json.load(f)
    random.shuffle(data)
    return data

def load_rules():
    rules = {}
    for filename in os.listdir(RULES_FOLDER):
        if filename.endswith(".txt"):
            category = filename.replace(".txt", "")
            with open(os.path.join(RULES_FOLDER, filename), encoding="utf-8") as f:
                rules[category] = f.read()
    return rules

RULES_BY_CATEGORY = load_rules()

# === OPENAI ===
async def evaluate_answer(entry, user_answer):
    question = entry["question"]
    expected_skill = entry["expected_skill"]
    category = entry["category"]
    rules = RULES_BY_CATEGORY.get(category, "")[:3000]

    prompt = f"""
Вопрос пользователя: {question}
Ответ оператора: {user_answer}
Навык: {expected_skill}
Категория: {category}

Правила:
{rules}

Дай честную оценку в формате JSON:
{{
  "evaluation": "correct|partial|incorrect",
  "reason": "пояснение почему такая оценка",
  "grammar_issues": "замечания по русскому языку",
  "correct_answer": "пример корректного ответа",
  "clarification": "уточняющий вопрос, если ответ неверный"
}}
Если ответ почти правильный — оценивай как "correct".
"""

    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        content = response["choices"][0]["message"]["content"]
        return json.loads(content)
    except Exception as e:
        logger.error(f"Ошибка ИИ: {e}")
        return {
            "evaluation": "incorrect",
            "reason": "ИИ не ответил",
            "grammar_issues": "",
            "correct_answer": "",
            "clarification": "ИИ временно недоступен. Попробуйте позже."
        }

# === AUTH FLOW ===
async def auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите логин:")
    return LOGIN

async def login_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["login"] = update.message.text
    await update.message.reply_text("Введите пароль:")
    return PASSWORD_STATE

async def password_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text
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
            await update.message.reply_text("Неверный пароль.")
    else:
        c.execute("INSERT INTO users (user_id, username, login, password) VALUES (?, ?, ?, ?)",
                  (user_id, username, login, password))
        session[user_id] = {"authenticated": True}
        await update.message.reply_text("Регистрация успешна. Напишите /start для начала.")
    conn.commit()
    conn.close()
    return ConversationHandler.END

# === ТРЕНИРОВКА ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in session or not session[user_id].get("authenticated"):
        await update.message.reply_text("Сначала авторизуйтесь через /auth.")
        return

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
    result = await evaluate_answer(entry, answer)

    evaluation = result["evaluation"]
    correct = result.get("correct_answer", "")
    clarification = result.get("clarification", "")
    grammar = result.get("grammar_issues", "")
    reason = result.get("reason", "")

    session[user_id]["last"] = {
        "question": entry["question"],
        "answer": answer,
        "evaluation": evaluation,
        "correct_answer": correct
    }

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        INSERT INTO logs (user_id, question, answer, evaluation, grammar_issues, correct_answer)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, entry["question"], answer, evaluation, grammar, correct))
    conn.commit()
    conn.close()

    session[user_id]["score"][evaluation] += 1

    if evaluation == "correct":
        await update.message.reply_text("✅ Верно!")
        session[user_id]["step"] += 1
        await ask_next(update, context)
    elif evaluation == "partial":
        await update.message.reply_text("🟡 Почти правильно. Попробуй дополнить.")
    else:
        await update.message.reply_text(f"❌ Не совсем то. {clarification or 'Попробуй иначе.'}")

async def show_correct(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    last = session.get(user_id, {}).get("last")
    if not last:
        await update.message.reply_text("Нет ответа для показа.")
        return
    await update.message.reply_text(f"Правильный ответ:\n{last['correct_answer']}")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    score = session.get(user_id, {}).get("score", {})
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
