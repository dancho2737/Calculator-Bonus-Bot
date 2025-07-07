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
BOT_TOKEN = os.environ["BOT_TOKEN"]
API_KEY = os.environ["OPENAI_KEY"]
openai.api_key = API_KEY

DB_FILE = "data.db"
SCENARIO_FILE = "scenarios.json"
RULES_FOLDER = "rules"
PASSWORD = "starzbot"

# === STATES ===
(
    PASSWORD_CHECK,
    REGISTRATION,
    LOGIN,
    AWAITING_ANSWER,
    AWAITING_FOLLOWUP_ANSWER,
) = range(5)

# === LOGGER ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

# === GLOBAL MEMORY ===
session = {}

# === LOAD SCENARIOS AND RULES ===
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
            path = os.path.join(RULES_FOLDER, filename)
            with open(path, encoding='utf-8') as f:
                rules[category] = f.read()
    return rules

RULES_BY_CATEGORY = load_rules()

# === AI EVALUATION ===
def evaluate_answer(question, expected_skill, category, answer):
    rules_text = RULES_BY_CATEGORY.get(category, "")[:3000]
    prompt = f"""
Вопрос оператора: {question}
Навык: {expected_skill}
Категория: {category}
Ответ оператора: {answer}

Правила:
{rules_text}

Ответь строго в формате JSON:
{{
  "evaluation": "correct|partial|incorrect",
  "reason": "...",
  "grammar_issues": "...",
  "correct_answer": "...",
  "follow_up_question": "..."
}}
Если ответ почти верный, но незначительно отличается от корректного, оценивай как "correct".
Если ответ неверный или частично верный — предложи уточняющий вопрос, чтобы помочь пользователю лучше ответить.
"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        content = response["choices"][0]["message"]["content"].strip()
        logger.info(f"OpenAI raw response: {content}")
        result = json.loads(content)
    except Exception as e:
        logger.error(f"Ошибка OpenAI: {e}")
        result = {"evaluation": "incorrect", "reason": "Ошибка анализа ИИ", "grammar_issues": "", "correct_answer": "", "follow_up_question": ""}
    return result

# === HANDLERS ===

async def start_training(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in session or not session[user_id].get("authenticated"):
        await update.message.reply_text("Сначала авторизуйтесь через /auth.")
        return

    session[user_id]["score"] = {"correct": 0, "partial": 0, "incorrect": 0}
    session[user_id]["step"] = 0
    session[user_id]["scenario"] = load_scenarios()
    session[user_id]["followup_mode"] = False
    session[user_id]["followup_tries"] = 0

    await ask_question(update, context)
    return AWAITING_ANSWER

async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    index = session[user_id]["step"]
    scenario = session[user_id]["scenario"]

    if index >= len(scenario):
        await update.message.reply_text("Тренировка завершена. Напишите /stop для просмотра статистики.")
        return ConversationHandler.END

    entry = scenario[index]
    session[user_id]["current"] = entry
    session[user_id]["followup_mode"] = False
    session[user_id]["followup_tries"] = 0
    await update.message.reply_text(f"Вопрос: {entry['question']}")

async def process_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    answer = update.message.text.strip()

    if user_id not in session or "current" not in session[user_id]:
        await update.message.reply_text("Пожалуйста, начните тренировку с команды /start.")
        return

    entry = session[user_id]["current"]
    followup_mode = session[user_id].get("followup_mode", False)
    followup_tries = session[user_id].get("followup_tries", 0)

    # Оцениваем ответ
    result = evaluate_answer(entry["question"], entry["expected_skill"], entry["category"], answer)
    evaluation = result.get("evaluation", "incorrect")
    reason = result.get("reason", "")
    grammar = result.get("grammar_issues", "")
    correct_answer = result.get("correct_answer", "")
    follow_up_question = result.get("follow_up_question", "")

    session[user_id]["last"] = {
        "question": entry["question"],
        "answer": answer,
        "evaluation": evaluation,
        "correct_answer": correct_answer
    }

    # Записываем в базу
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        INSERT INTO logs (user_id, question, answer, evaluation, grammar_issues, correct_answer)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, entry["question"], answer, evaluation, grammar, correct_answer))
    conn.commit()
    conn.close()

    # Обновляем счётчик
    session[user_id]["score"][evaluation] += 1

    if evaluation == "correct":
        await update.message.reply_text("✅ Ответ засчитан как верный!")
        session[user_id]["step"] += 1
        session[user_id]["followup_mode"] = False
        session[user_id]["followup_tries"] = 0
        await ask_question(update, context)
    else:
        # Если мы уже в режиме уточнений — считаем попытку
        if followup_mode:
            session[user_id]["followup_tries"] += 1
            if session[user_id]["followup_tries"] >= 3:
                await update.message.reply_text(f"❌ Всё равно неверно. Правильный ответ:\n{correct_answer}")
                session[user_id]["step"] += 1
                session[user_id]["followup_mode"] = False
                session[user_id]["followup_tries"] = 0
                await ask_question(update, context)
            else:
                await update.message.reply_text(f"❌ Ответ всё ещё неверный. Попробуйте иначе.\nУточнение: {follow_up_question}")
        else:
            # Включаем режим уточнений
            session[user_id]["followup_mode"] = True
            session[user_id]["followup_tries"] = 1
            await update.message.reply_text(f"🟡 Ответ неверный или частично верный.\nУточняющий вопрос: {follow_up_question}")

async def send_correct_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    last = session.get(user_id, {}).get("last")
    if not last:
        await update.message.reply_text("Нет ответа для показа.")
        return
    correct = last.get("correct_answer", "Нет правильного ответа.")
    await update.message.reply_text(f"Правильный ответ:\n{correct}")

async def stop_training(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    score = session.get(user_id, {}).get("score", {})
    msg = (f"Статистика:\n"
           f"✅ Верных: {score.get('correct', 0)}\n"
           f"🟡 Частично верных: {score.get('partial', 0)}\n"
           f"❌ Неверных: {score.get('incorrect', 0)}")
    await update.message.reply_text(msg)

async def report_error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    last = session.get(user_id, {}).get("last")
    if not last:
        await update.message.reply_text("Нет последнего ответа для жалобы.")
        return
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO error_reports (user_id, question, answer, evaluation) VALUES (?, ?, ?, ?)",
              (user_id, last["question"], last["answer"], last["evaluation"]))
    conn.commit()
    conn.close()
    await update.message.reply_text("Жалоба отправлена. Спасибо!")

# === MAIN ===
if __name__ == '__main__':
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    from auth_handlers import conv_handler as auth_conv
    app.add_handler(auth_conv)

    app.add_handler(CommandHandler("start", start_training))
    app.add_handler(CommandHandler("stop", stop_training))
    app.add_handler(CommandHandler("answer", send_correct_answer))
    app.add_handler(CommandHandler("error", report_error))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_answer))

    app.run_polling()
