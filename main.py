import logging
import sqlite3
import json
import os
import random
import time
import asyncio

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    MessageHandler, filters, CallbackQueryHandler, ConversationHandler
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

# === STATE ===
(
    PASSWORD_CHECK,
    REGISTRATION,
    LOGIN,
    AWAITING_ANSWER,
) = range(4)

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
            grammar_issues TEXT
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
    all_rules = []
    for filename in os.listdir(RULES_FOLDER):
        path = os.path.join(RULES_FOLDER, filename)
        if os.path.isfile(path):
            with open(path, encoding='utf-8') as f:
                all_rules.append(f.read())
    return "\n".join(all_rules)

RULE_TEXT = load_rules()

# === AI EVALUATION ===
def evaluate_answer(question, expected_skill, answer):
    prompt = f"""
Вопрос оператора: {question}
Навык, который оценивается: {expected_skill}
Ответ оператора: {answer}

Оцени ответ по следующим критериям:
1. Правильный
2. Правильный, но неполный
3. Неправильный

Также сравни ответ с внутренними правилами поддержки:
{RULE_TEXT[:5000]}

Ответь строго в формате JSON:
{{"evaluation": "correct|partial|incorrect", "reason": "...", "grammar_issues": "..."}}
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
        logger.error(f"Ошибка парсинга ответа ИИ или вызова OpenAI: {e}")
        result = {"evaluation": "incorrect", "reason": "Ошибка анализа ответа ИИ", "grammar_issues": ""}
    return result

# === HANDLERS ===
# ... Все хендлеры без изменений (auth_start, password_check и др.) ...

# === MAIN ===
if __name__ == '__main__':
    print("⏳ Подготовка к запуску...")
    time.sleep(3)
    init_db()

    print("🚀 Запуск Telegram-бота...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # ConversationHandler для авторизации
    conv = ConversationHandler(
        entry_points=[CommandHandler("auth", auth_start)],
        states={
            PASSWORD_CHECK: [MessageHandler(filters.TEXT & ~filters.COMMAND, password_check)],
            REGISTRATION: [CallbackQueryHandler(button_handler)],
            LOGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_handler)],
        },
        fallbacks=[]
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("start", start_training))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_answer))
    app.add_handler(CommandHandler("stop", stop_training))
    app.add_handler(CommandHandler("error", report_error))

    try:
        app.run_polling()
    except Exception as e:
        logger.error(f"Ошибка запуска бота: {e}")
