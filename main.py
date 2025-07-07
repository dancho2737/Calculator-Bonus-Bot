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

# === CONFIG ===
BOT_TOKEN = os.environ.get("BOT_TOKEN")
OPENAI_KEY = os.environ.get("OPENAI_KEY")
openai.api_key = OPENAI_KEY

db_file = "data.db"
scenarios_file = "scenarios.json"
rules_folder = "rules"
PASSWORD = "starzbot"

(
    PASSWORD_CHECK,
    REGISTRATION,
    LOGIN,
    AWAITING_ANSWER,
) = range(4)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === DATABASE INIT ===
def init_db():
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        login TEXT,
        password TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        question TEXT,
        answer TEXT,
        evaluation TEXT,
        grammar_issues TEXT,
        correct_answer TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS error_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        question TEXT,
        answer TEXT,
        evaluation TEXT)''')
    conn.commit()
    conn.close()

# === MEMORY ===
session = {}

# === RULES/SCENARIOS ===
def load_scenarios():
    with open(scenarios_file, encoding='utf-8') as f:
        data = json.load(f)
    random.shuffle(data)
    return data

def load_rules():
    rules = {}
    for file in os.listdir(rules_folder):
        if file.endswith(".txt"):
            with open(os.path.join(rules_folder, file), encoding='utf-8') as f:
                rules[file.replace(".txt", "")] = f.read()
    return rules

RULES_BY_CATEGORY = load_rules()

# === AUTH ===
from telegram import ReplyKeyboardMarkup

authenticated_users = set()

async def auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text("Введите пароль:")
    return PASSWORD_CHECK

async def check_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.strip() == PASSWORD:
        user_id = update.effective_user.id
        authenticated_users.add(user_id)
        session[user_id] = {"authenticated": True}
        await update.message.reply_text("Успешная авторизация! Введите /start для начала тренировки.")
        return ConversationHandler.END
    await update.message.reply_text("Неверный пароль. Попробуйте снова через /auth.")
    return ConversationHandler.END

# === AI ===
def is_ai_available():
    try:
        openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Ping"}],
            max_tokens=1
        )
        return True
    except:
        return False

def evaluate_answer(question, expected_skill, category, answer):
    rules = RULES_BY_CATEGORY.get(category, "")[:3000]
    prompt = f"""
Вопрос от пользователя: {question}
Навык: {expected_skill}
Категория: {category}
Ответ оператора: {answer}
Правила:
{rules}

Ответь строго в JSON:
{{
  "evaluation": "correct|partial|incorrect",
  "reason": "...",
  "grammar_issues": "...",
  "correct_answer": "...",
  "followup": "..."
}}
"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        result = json.loads(response.choices[0].message.content)
        return result
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        return {
            "evaluation": "incorrect",
            "reason": "ИИ недоступен.",
            "grammar_issues": "",
            "correct_answer": "",
            "followup": "Попробуйте позже."
        }

# === TRAINING ===
async def start_training(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in authenticated_users:
        await update.message.reply_text("Сначала авторизуйтесь через /auth.")
        return

    session[user_id] = {
        "authenticated": True,
        "score": {"correct": 0, "partial": 0, "incorrect": 0},
        "step": 0,
        "scenario": load_scenarios()
    }
    await ask_question(update, context)
    return AWAITING_ANSWER

async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    index = session[user_id]["step"]
    scenario = session[user_id]["scenario"]
    if index >= len(scenario):
        await update.message.reply_text("Тренировка завершена. /stop для статистики.")
        return ConversationHandler.END

    entry = scenario[index]
    session[user_id]["current"] = entry
    await update.message.reply_text(f"Вопрос: {entry['question']}")

async def process_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    answer = update.message.text.strip()
    entry = session[user_id].get("current")
    if not entry:
        await update.message.reply_text("Сначала начните тренировку с /start")
        return

    result = evaluate_answer(entry["question"], entry["expected_skill"], entry["category"], answer)
    evaluation = result.get("evaluation")
    followup = result.get("followup", "")
    correct_answer = result.get("correct_answer", "")

    session[user_id]["last"] = {
        "question": entry["question"],
        "answer": answer,
        "evaluation": evaluation,
        "correct_answer": correct_answer
    }

    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute("INSERT INTO logs (user_id, question, answer, evaluation, grammar_issues, correct_answer) VALUES (?, ?, ?, ?, ?, ?)",
              (user_id, entry["question"], answer, evaluation, result.get("grammar_issues"), correct_answer))
    conn.commit()
    conn.close()

    session[user_id]["score"][evaluation] += 1

    if evaluation == "correct":
        await update.message.reply_text("✅ Верный ответ!")
        session[user_id]["step"] += 1
        await ask_question(update, context)
    elif evaluation == "partial":
        await update.message.reply_text("🟡 Ответ частично верный. Попробуйте раскрыть подробнее.")
    else:
        await update.message.reply_text(f"❌ Ответ неверный. {followup} Напишите /answer чтобы посмотреть правильный.")

async def send_correct_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    correct = session.get(user_id, {}).get("last", {}).get("correct_answer", "Нет данных.")
    await update.message.reply_text(f"Правильный ответ:\n{correct}")

async def stop_training(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    score = session.get(user_id, {}).get("score", {})
    await update.message.reply_text(
        f"Статистика:\n✅ Верных: {score.get('correct', 0)}\n🟡 Частичных: {score.get('partial', 0)}\n❌ Неверных: {score.get('incorrect', 0)}")

async def report_error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    last = session.get(user_id, {}).get("last")
    if not last:
        await update.message.reply_text("Нет ответа для жалобы.")
        return
    conn = sqlite3.connect(db_file)
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

    if is_ai_available():
        logger.info("✅ ИИ активен и работает.")
    else:
        logger.warning("⚠️ ИИ не отвечает. Ответы не будут оценены.")

    auth_conv = ConversationHandler(
        entry_points=[CommandHandler("auth", auth)],
        states={PASSWORD_CHECK: [MessageHandler(filters.TEXT, check_password)]},
        fallbacks=[]
    )
    app.add_handler(auth_conv)

    app.add_handler(CommandHandler("start", start_training))
    app.add_handler(CommandHandler("stop", stop_training))
    app.add_handler(CommandHandler("answer", send_correct_answer))
    app.add_handler(CommandHandler("error", report_error))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_answer))

    app.run_polling()
