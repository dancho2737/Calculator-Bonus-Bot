import logging
import sqlite3
import json
import os
import random

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    MessageHandler, filters, ConversationHandler, CallbackQueryHandler
)

import openai

# === CONFIG ===
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
API_KEY = os.environ.get("OPENAI_KEY", "")
openai.api_key = API_KEY

DB_FILE = "data.db"
SCENARIO_FILE = "scenarios.json"
RULES_FOLDER = "rules"
PASSWORD = "starzbot"

# === STATES ===
(PASSWORD_CHECK, REGISTRATION, LOGIN, AWAITING_ANSWER) = range(4)

# === LOGGER ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === SESSION ===
session = {}

# === INIT DB ===
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            login TEXT,
            password TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            question TEXT,
            answer TEXT,
            evaluation TEXT,
            grammar_issues TEXT,
            correct_answer TEXT
        )
    """)
    conn.commit()
    conn.close()

# === SCENARIOS ===
def load_scenarios():
    with open(SCENARIO_FILE, encoding='utf-8') as f:
        data = json.load(f)
    random.shuffle(data)
    return data

# === RULES ===
def load_rules():
    rules = {}
    for filename in os.listdir(RULES_FOLDER):
        if filename.endswith(".txt"):
            path = os.path.join(RULES_FOLDER, filename)
            with open(path, encoding='utf-8') as f:
                rules[filename.replace('.txt', '')] = f.read()
    return rules

RULES_BY_CATEGORY = load_rules()

# === AI ===
def test_openai():
    try:
        openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1
        )
        return True
    except Exception as e:
        logger.warning("OpenAI недоступен: %s", e)
        return False

def evaluate_answer(question, expected_skill, category, answer):
    rules_text = RULES_BY_CATEGORY.get(category, "")[:3000]
    prompt = f"""
Вопрос пользователя: {question}
Навык: {expected_skill}
Категория: {category}
Ответ оператора: {answer}

Правила сайта:
{rules_text}

Оцени ответ по правилам. Ответь строго в формате JSON:
{{
  "evaluation": "correct|partial|incorrect",
  "reason": "...",
  "followup_question": "...",
  "grammar_issues": "...",
  "correct_answer": "..."
}}
Если ответ близок, но не дословный, всё равно считай как "correct".
"""

    try:
        res = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        content = res["choices"][0]["message"]["content"].strip()
        return json.loads(content)
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        return {
            "evaluation": "incorrect",
            "reason": "ИИ недоступен",
            "followup_question": "",
            "grammar_issues": "",
            "correct_answer": ""
        }

# === HANDLERS ===
async def auth_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите пароль доступа:")
    return PASSWORD_CHECK

async def password_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.strip() == PASSWORD:
        keyboard = [
            [InlineKeyboardButton("Зарегистрироваться", callback_data="register")],
            [InlineKeyboardButton("Войти", callback_data="login")]
        ]
        await update.message.reply_text("Добро пожаловать!", reply_markup=InlineKeyboardMarkup(keyboard))
        return ConversationHandler.END
    else:
        await update.message.reply_text("Неверный пароль.")
        return ConversationHandler.END

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "register":
        await query.edit_message_text("Введите логин для регистрации:")
        return REGISTRATION
    else:
        await query.edit_message_text("Введите логин для входа:")
        return LOGIN

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username
    login = update.message.text.strip()
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users (user_id, username, login, password) VALUES (?, ?, ?, ?)",
              (user_id, username, login, PASSWORD))
    conn.commit()
    conn.close()
    session[user_id] = {"authenticated": True}
    await update.message.reply_text("Вы успешно зарегистрированы!")
    return ConversationHandler.END

async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    login = update.message.text.strip()
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ? AND login = ?", (user_id, login))
    user = c.fetchone()
    conn.close()
    if user:
        session[user_id] = {"authenticated": True}
        await update.message.reply_text("Вход выполнен.")
    else:
        await update.message.reply_text("Неверный логин.")
    return ConversationHandler.END

# === Тренировка ===
async def start_training(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in session or not session[user_id].get("authenticated"):
        await update.message.reply_text("Сначала авторизуйтесь через /auth.")
        return

    session[user_id]["score"] = {"correct": 0, "partial": 0, "incorrect": 0}
    session[user_id]["step"] = 0
    session[user_id]["scenario"] = load_scenarios()
    await ask_question(update, context)
    return AWAITING_ANSWER

async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    index = session[user_id]["step"]
    scenario = session[user_id]["scenario"]
    if index >= len(scenario):
        await update.message.reply_text("Тренировка завершена. Напишите /stop.")
        return ConversationHandler.END
    entry = scenario[index]
    session[user_id]["current"] = entry
    await update.message.reply_text(f"Вопрос: {entry['question']}")

async def process_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in session or "current" not in session[user_id]:
        await update.message.reply_text("Сначала начните тренировку с /start.")
        return

    answer = update.message.text.strip()
    entry = session[user_id]["current"]
    result = evaluate_answer(entry["question"], entry["expected_skill"], entry["category"], answer)

    evaluation = result.get("evaluation", "incorrect")
    correct_answer = result.get("correct_answer", "")
    followup = result.get("followup_question", "")
    reason = result.get("reason", "")
    grammar = result.get("grammar_issues", "")

    session[user_id]["last"] = {
        "question": entry["question"],
        "answer": answer,
        "evaluation": evaluation,
        "correct_answer": correct_answer
    }

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""INSERT INTO logs (user_id, question, answer, evaluation, grammar_issues, correct_answer)
                 VALUES (?, ?, ?, ?, ?, ?)""",
              (user_id, entry["question"], answer, evaluation, grammar, correct_answer))
    conn.commit()
    conn.close()

    session[user_id]["score"][evaluation] += 1

    if evaluation == "correct":
        await update.message.reply_text("✅ Верно! Следующий вопрос:")
        session[user_id]["step"] += 1
        await ask_question(update, context)
    elif evaluation == "partial":
        await update.message.reply_text(f"🟡 Почти верно. Попробуйте дополнить.\nПричина: {reason}")
    else:
        message = f"❌ Неверно. Причина: {reason}"
        if followup:
            message += f"\n🤔 Подсказка: {followup}"
        await update.message.reply_text(message)

async def send_correct_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    last = session.get(user_id, {}).get("last")
    if not last:
        await update.message.reply_text("Нет ответа.")
        return
    correct = last.get("correct_answer", "Не указано.")
    await update.message.reply_text(f"Правильный ответ:\n{correct}")

async def stop_training(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    score = session.get(user_id, {}).get("score", {})
    msg = (f"Статистика:\n"
           f"✅ Верных: {score.get('correct', 0)}\n"
           f"🟡 Частично: {score.get('partial', 0)}\n"
           f"❌ Неверных: {score.get('incorrect', 0)}")
    await update.message.reply_text(msg)

# === MAIN ===
if __name__ == '__main__':
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("auth", auth_start)],
        states={
            PASSWORD_CHECK: [MessageHandler(filters.TEXT & ~filters.COMMAND, password_check)],
            REGISTRATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, register)],
            LOGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, login)],
        },
        fallbacks=[],
        allow_reentry=True
    ))
    app.add_handler(CallbackQueryHandler(button_handler))

    app.add_handler(CommandHandler("start", start_training))
    app.add_handler(CommandHandler("stop", stop_training))
    app.add_handler(CommandHandler("answer", send_correct_answer))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_answer))

    if test_openai():
        print("✅ OpenAI ИИ подключён и работает.")
    else:
        print("⚠️ OpenAI ИИ неактивен или недоступен.")

    app.run_polling()
