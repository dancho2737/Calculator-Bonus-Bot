import logging
import sqlite3
import json
import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ApplicationBuilder, CommandHandler, ContextTypes,
                          MessageHandler, filters, CallbackQueryHandler, ConversationHandler)

import openai

# === CONFIG ===
BOT_TOKEN = "BOT_TOKEN"
API_KEY = "openAI_key"
openai.api_key = API_KEY
DB_FILE = "data.db"
SCENARIO_FILE = "scenarios.json"
RULES_FOLDER = "rules"
PASSWORD = "starzbot"

# === STATE ===
(ASKING_QUESTION, AWAITING_ANSWER, PASSWORD_CHECK, REGISTRATION, LOGIN) = range(5)

# === LOGGER ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === DATABASE ===
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    login TEXT,
                    password TEXT
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    question TEXT,
                    answer TEXT,
                    evaluation TEXT,
                    grammar_issues TEXT
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS error_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    question TEXT,
                    answer TEXT,
                    evaluation TEXT
                )''')
    conn.commit()
    conn.close()

# === GLOBAL MEMORY ===
session = {}

# === LOAD SCENARIOS ===
def load_scenarios():
    with open(SCENARIO_FILE, encoding='utf-8') as f:
        return json.load(f)

# === LOAD RULES ===
def load_rules():
    all_rules = []
    for filename in os.listdir(RULES_FOLDER):
        path = os.path.join(RULES_FOLDER, filename)
        if os.path.isfile(path):
            with open(path, encoding='utf-8') as f:
                all_rules.append(f.read())
    return "\n".join(all_rules)

RULE_TEXT = load_rules()

# === AI PROMPT ===
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

Ответь строго в формате:
{{"evaluation": "correct|partial|incorrect", "reason": "...", "grammar_issues": "..."}}
"""
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    result = json.loads(response["choices"][0]["message"]["content"].strip())
    return result

# === HANDLERS ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in session:
        session[user_id] = {"authenticated": False}
    if not session[user_id]["authenticated"]:
        await update.message.reply_text("Введите пароль для доступа:")
        return PASSWORD_CHECK
    await update.message.reply_text("Добро пожаловать! Используйте /start для начала.")
    return ConversationHandler.END

async def password_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == PASSWORD:
        keyboard = [[InlineKeyboardButton("Зарегистрироваться", callback_data='register')],
                    [InlineKeyboardButton("Войти", callback_data='login')]]
        await update.message.reply_text("Пароль верен. Выберите действие:",
                                        reply_markup=InlineKeyboardMarkup(keyboard))
        return REGISTRATION
    await update.message.reply_text("Неверный пароль. Попробуйте снова.")
    return PASSWORD_CHECK

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    session[user_id]["action"] = query.data
    await query.message.reply_text("Введите логин:")
    return LOGIN

async def login_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    state = session[user_id]
    if "login" not in state:
        state["login"] = text
        await update.message.reply_text("Введите пароль:")
        return LOGIN
    login, password = state["login"], text
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    if state["action"] == "register":
        c.execute("INSERT OR REPLACE INTO users (user_id, username, login, password) VALUES (?, ?, ?, ?)",
                  (user_id, update.effective_user.username, login, password))
        conn.commit()
        await update.message.reply_text("Регистрация прошла успешно. Введите /start для начала тренировки.")
    else:
        c.execute("SELECT * FROM users WHERE login = ? AND password = ?", (login, password))
        if not c.fetchone():
            await update.message.reply_text("Неверный логин или пароль. Попробуйте снова.")
            return LOGIN
        await update.message.reply_text("Успешный вход. Введите /start для начала тренировки.")
    session[user_id]["authenticated"] = True
    conn.close()
    return ConversationHandler.END

async def start_training(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in session or not session[user_id].get("authenticated"):
        await update.message.reply_text("Сначала авторизуйтесь через /start.")
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
        await update.message.reply_text("Тренировка завершена. Напишите /stop для статистики.")
        return
    question = scenario[index]["question"]
    await update.message.reply_text(f"Вопрос: {question}")

async def process_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    scenario = session[user_id]["scenario"]
    index = session[user_id]["step"]
    entry = scenario[index]
    answer = update.message.text
    result = evaluate_answer(entry["question"], entry["expected_skill"], answer)
    evaluation = result["evaluation"]
    grammar = result.get("grammar_issues", "")

    session[user_id]["score"][evaluation] += 1
    session[user_id]["last"] = {"question": entry["question"], "answer": answer, "evaluation": evaluation}

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO logs (user_id, question, answer, evaluation, grammar_issues) VALUES (?, ?, ?, ?, ?)",
              (user_id, entry["question"], answer, evaluation, grammar))
    conn.commit()
    conn.close()

    if evaluation == "correct":
        await update.message.reply_text("✅ Ответ верный!")
        session[user_id]["step"] += 1
        await ask_question(update, context)
    elif evaluation == "partial":
        await update.message.reply_text("🟡 Ответ частично верный. Попробуйте дополнить.")
    else:
        await update.message.reply_text("❌ Неверный ответ. Попробуйте снова, уточните детали.")

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

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            PASSWORD_CHECK: [MessageHandler(filters.TEXT & ~filters.COMMAND, password_check)],
            REGISTRATION: [CallbackQueryHandler(button_handler)],
            LOGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_handler)],
            AWAITING_ANSWER: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_answer)],
        },
        fallbacks=[]
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("start", start_training))
    app.add_handler(CommandHandler("stop", stop_training))
    app.add_handler(CommandHandler("ошибка", report_error))

    app.run_polling()

