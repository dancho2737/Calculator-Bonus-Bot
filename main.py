import logging
import sqlite3
import json
import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ApplicationBuilder, CommandHandler, ContextTypes,
                          MessageHandler, filters, CallbackQueryHandler, ConversationHandler)

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
PASSWORD_CHECK, ACTION_SELECT, LOGIN_USERNAME, LOGIN_PASSWORD, TRAINING = range(5)

# === LOGGING ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === DATABASE ===
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    login TEXT UNIQUE,
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

# === LOAD SCENARIOS ===
def load_scenarios():
    with open(SCENARIO_FILE, encoding='utf-8') as f:
        return json.load(f)

# === LOAD RULES ===
def load_rules():
    texts = []
    for filename in os.listdir(RULES_FOLDER):
        path = os.path.join(RULES_FOLDER, filename)
        if os.path.isfile(path):
            with open(path, encoding='utf-8') as f:
                texts.append(f.read())
    return "\n".join(texts)

RULES_TEXT = load_rules()

# === AI PROMPT ===
def evaluate_answer(question, expected_skill, answer):
    prompt = f"""
Вопрос оператора: {question}
Навык, который оценивается: {expected_skill}
Ответ оператора: {answer}

Оцени ответ по следующим критериям:
1. correct - Правильный
2. partial - Правильный, но неполный
3. incorrect - Неправильный

Также сверяй ответ с внутренними правилами поддержки:
{RULES_TEXT[:5000]}

Ответь строго в формате JSON, например:
{{"evaluation": "correct", "reason": "...", "grammar_issues": "..."}}
"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        content = response["choices"][0]["message"]["content"].strip()
        result = json.loads(content)
        return result
    except Exception as e:
        logger.error(f"OpenAI API or JSON parse error: {e}")
        return {"evaluation": "incorrect", "reason": "Ошибка анализа ответа ИИ", "grammar_issues": ""}

# === GLOBAL SESSION ===
session = {}

# === HANDLERS ===

# /start первая команда — запрос пароля или приветствие
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in session or not session[user_id].get("authenticated", False):
        session[user_id] = {"authenticated": False}
        await update.message.reply_text("Введите пароль для доступа:")
        return PASSWORD_CHECK
    else:
        await update.message.reply_text("Вы уже авторизованы! Введите /start для начала тренировки.")
        return ConversationHandler.END

# Проверка пароля
async def password_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    if text == PASSWORD:
        keyboard = [
            [InlineKeyboardButton("Зарегистрироваться", callback_data='register')],
            [InlineKeyboardButton("Войти", callback_data='login')]
        ]
        await update.message.reply_text("Пароль верен. Выберите действие:",
                                        reply_markup=InlineKeyboardMarkup(keyboard))
        return ACTION_SELECT
    else:
        await update.message.reply_text("Неверный пароль. Попробуйте снова.")
        return PASSWORD_CHECK

# Обработка кнопок регистрации/входа
async def action_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    action = query.data  # 'register' или 'login'
    session[user_id]["action"] = action
    await query.message.reply_text("Введите логин:")
    return LOGIN_USERNAME

# Получаем логин
async def login_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    login = update.message.text.strip()
    session[user_id]["login"] = login
    await update.message.reply_text("Введите пароль:")
    return LOGIN_PASSWORD

# Получаем пароль и выполняем регистрацию или вход
async def login_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    password = update.message.text.strip()
    login = session[user_id].get("login")
    action = session[user_id].get("action")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    if action == "register":
        try:
            c.execute("INSERT INTO users (user_id, username, login, password) VALUES (?, ?, ?, ?)",
                      (user_id, update.effective_user.username, login, password))
            conn.commit()
        except sqlite3.IntegrityError:
            await update.message.reply_text("Этот логин уже занят. Попробуйте другой.")
            conn.close()
            return LOGIN_USERNAME
        await update.message.reply_text("Регистрация прошла успешно! Введите /start для начала тренировки.")
        session[user_id]["authenticated"] = True
    else:  # login
        c.execute("SELECT * FROM users WHERE login = ? AND password = ?", (login, password))
        user = c.fetchone()
        if not user:
            await update.message.reply_text("Неверный логин или пароль. Попробуйте снова.")
            conn.close()
            return LOGIN_USERNAME
        session[user_id]["authenticated"] = True
        await update.message.reply_text("Вход успешен! Введите /start для начала тренировки.")

    conn.close()
    return ConversationHandler.END

# Начало тренировки после авторизации
async def start_training(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in session or not session[user_id].get("authenticated", False):
        await update.message.reply_text("Сначала авторизуйтесь через /start.")
        return
    # Загружаем сценарий и обнуляем счетчики
    session[user_id]["scenario"] = load_scenarios()
    session[user_id]["step"] = 0
    session[user_id]["score"] = {"correct": 0, "partial": 0, "incorrect": 0}
    session[user_id]["last"] = None
    await ask_question(update, context)
    return TRAINING

async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    step = session[user_id]["step"]
    scenario = session[user_id]["scenario"]
    if step >= len(scenario):
        await update.message.reply_text("Тренировка завершена. Напишите /stop для просмотра статистики.")
        return
    question = scenario[step]["question"]
    await update.message.reply_text(f"Вопрос:\n{question}")

# Обработка ответов от оператора
async def process_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if user_id not in session or "scenario" not in session[user_id]:
        await update.message.reply_text("Пожалуйста, сначала начните тренировку с /start.")
        return

    step = session[user_id]["step"]
    scenario = session[user_id]["scenario"]
    if step >= len(scenario):
        await update.message.reply_text("Тренировка уже завершена. Напишите /stop для просмотра статистики.")
        return

    entry = scenario[step]

    # Оцениваем ответ ИИ
    result = evaluate_answer(entry["question"], entry.get("expected_skill", ""), text)
    evaluation = result.get("evaluation", "incorrect")
    grammar_issues = result.get("grammar_issues", "")

    # Логируем ответ
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "INSERT INTO logs (user_id, question, answer, evaluation, grammar_issues) VALUES (?, ?, ?, ?, ?)",
        (user_id, entry["question"], text, evaluation, grammar_issues)
    )
    conn.commit()
    conn.close()

    # Обновляем счет
    session[user_id]["score"][evaluation] += 1
    session[user_id]["last"] = {"question": entry["question"], "answer": text, "evaluation": evaluation}

    if evaluation == "correct":
        await update.message.reply_text("✅ Ответ верный!")
        session[user_id]["step"] += 1
        await ask_question(update, context)
    elif evaluation == "partial":
        await update.message.reply_text("🟡 Ответ частично верный. Попробуйте дополнить.")
    else:
        await update.message.reply_text("❌ Неверный ответ. Попробуйте снова, уточните детали.")

# Остановка тренировки и вывод статистики
async def stop_training(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    score = session.get(user_id, {}).get("score", {"correct": 0, "partial": 0, "incorrect": 0})
    msg = (f"Статистика тренировки:\n"
           f"✅ Верных ответов: {score.get('correct', 0)}\n"
           f"🟡 Частично верных: {score.get('partial', 0)}\n"
           f"❌ Неверных: {score.get('incorrect', 0)}")
    await update.message.reply_text(msg)

# Жалоба на оценку
async def report_error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    last = session.get(user_id, {}).get("last")
    if not last:
        await update.message.reply_text("Нет последнего ответа для жалобы.")
        return
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "INSERT INTO error_reports (user_id, question, answer, evaluation) VALUES (?, ?, ?, ?)",
        (user_id, last["question"], last["answer"], last["evaluation"])
    )
    conn.commit()
    conn.close()
    await update.message.reply_text("Жалоба принята. Спасибо за обратную связь!")

# === MAIN ===
if __name__ == "__main__":
    init_db()

    application = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            PASSWORD_CHECK: [MessageHandler(filters.TEXT & ~filters.COMMAND, password_check)],
            ACTION_SELECT: [CallbackQueryHandler(action_select)],
            LOGIN_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_username)],
            LOGIN_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_password)],
            TRAINING: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_answer)],
        },
        fallbacks=[]
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("start", start_training))  # Запуск тренировки
    application.add_handler(CommandHandler("stop", stop_training))    # Остановка и статистика
    application.add_handler(CommandHandler("error", report_error))    # Жалоба на оценку

    application.run_polling()
