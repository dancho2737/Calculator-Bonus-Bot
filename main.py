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
from prompts import TRAINING_PROMPT  # импорт промпта из prompts.py

# === CONFIG ===
BOT_TOKEN = os.environ["BOT_TOKEN"]
API_KEY = os.environ["OPENAI_KEY"]
openai.api_key = API_KEY

DB_FILE = "data.db"
SCENARIO_FILE = "scenarios.json"
RULES_FOLDER = "rules"
BOT_PASSWORD = "starzbot"
ADMIN_PASSWORD = "starz123321"

# === STATES ===
(
    PASSWORD_STATE, AUTH_CHOICE, REGISTER_LOGIN, REGISTER_PASS,
    LOGIN_LOGIN, LOGIN_PASS,
    TRAINING, AWAITING_ANSWER,
    ADMIN_PASS, ADMIN_CMD,
    ERROR_REPORT
) = range(11)

# === LOGGER ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === SESSION ===
session = {}

# === Глобальная переменная для правил ===
rules_data = {}

# === Загрузка правил из папки rules/ ===
def load_rules():
    rules = {}
    if not os.path.exists(RULES_FOLDER):
        logger.warning(f"Папка с правилами '{RULES_FOLDER}' не найдена!")
        return rules
    for filename in os.listdir(RULES_FOLDER):
        if filename.endswith(".txt"):
            path = os.path.join(RULES_FOLDER, filename)
            with open(path, encoding="utf-8") as f:
                key = os.path.splitext(filename)[0].lower()
                rules[key] = f.read()
    logger.info(f"Загружено правил из {len(rules)} файлов.")
    return rules

# === DATABASE INIT ===
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Пользователи
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            login TEXT UNIQUE,
            password TEXT
        )
    ''')
    # Логи тренировок
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
    # Жалобы (ошибки)
    c.execute('''
        CREATE TABLE IF NOT EXISTS error_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            question TEXT,
            answer TEXT,
            evaluation TEXT
        )
    ''')
    # Ошибки с ID для /mistake и /done
    c.execute('''
        CREATE TABLE IF NOT EXISTS mistakes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            question TEXT,
            answer TEXT,
            evaluation TEXT,
            resolved INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

# === Загрузка сценариев ===
def load_scenarios():
    with open(SCENARIO_FILE, encoding='utf-8') as f:
        data = json.load(f)
    random.shuffle(data)
    return data

# === Оценка ответов ИИ ===
async def evaluate_answer(entry, user_answer, rules_data):
    question = entry["question"]
    expected_answer = entry["expected_answer"]

    combined_rules = "\n\n".join(rules_data.values())

    prompt = TRAINING_PROMPT.format(
        question=question,
        expected_answer=expected_answer
    )
    prompt += f"\n\nПравила сайта:\n{combined_rules}\n\nОтвет оператора:\n{user_answer}"

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
        return content
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        return "Ошибка при оценке ИИ. Попробуйте позже."

# === /auth ===
async def auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔐 Введите пароль для доступа к боту:")
    return PASSWORD_STATE

async def password_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip()
    if password == BOT_PASSWORD:
        keyboard = [
            [InlineKeyboardButton("Регистрация", callback_data="register")],
            [InlineKeyboardButton("Вход", callback_data="login")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("✅ Пароль принят! Выберите действие:", reply_markup=reply_markup)
        return AUTH_CHOICE
    else:
        await update.message.reply_text("❌ Неверный пароль. Попробуйте снова через /auth.")
        return ConversationHandler.END

async def auth_choice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    choice = query.data

    if choice == "register":
        await query.edit_message_text("Введите новый логин для регистрации:")
        return REGISTER_LOGIN
    elif choice == "login":
        await query.edit_message_text("Введите логин для входа:")
        return LOGIN_LOGIN

async def register_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    login = update.message.text.strip()
    context.user_data['register_login'] = login
    await update.message.reply_text("Введите пароль для регистрации:")
    return REGISTER_PASS

async def register_pass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip()
    login = context.user_data.get('register_login')
    user_id = update.effective_user.id
    username = update.effective_user.username

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("SELECT * FROM users WHERE login=?", (login,))
    if c.fetchone():
        await update.message.reply_text("❌ Такой логин уже существует. Введите другой логин или начните заново через /auth.")
        conn.close()
        return ConversationHandler.END

    c.execute("INSERT INTO users (user_id, username, login, password) VALUES (?, ?, ?, ?)",
              (user_id, username, login, password))
    conn.commit()
    conn.close()

    session[user_id] = {"authenticated": True, "login": login}
    await update.message.reply_text("✅ Регистрация успешна! Напишите /start для начала тренировки.")
    return ConversationHandler.END

async def login_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    login = update.message.text.strip()
    context.user_data['login_login'] = login
    await update.message.reply_text("Введите пароль для входа:")
    return LOGIN_PASS

async def login_pass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip()
    login = context.user_data.get('login_login')
    user_id = update.effective_user.id

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE login=? AND password=?", (login, password))
    user = c.fetchone()
    conn.close()

    if user:
        session[user_id] = {"authenticated": True, "login": login}
        await update.message.reply_text("✅ Вход выполнен успешно! Напишите /start для начала тренировки.")
        return ConversationHandler.END
    else:
        await update.message.reply_text("❌ Неверный логин или пароль. Попробуйте /auth снова.")
        return ConversationHandler.END

# === /start - начало тренировки ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in session or not session[user_id].get("authenticated"):
        await update.message.reply_text("Сначала авторизуйтесь через /auth.")
        return ConversationHandler.END

    if session[user_id].get("is_admin_conversation"):
        session[user_id]["is_admin_conversation"] = False

    scenario = load_scenarios()
    session[user_id]["scenario"] = scenario
    session[user_id]["step"] = 0
    session[user_id]["score"] = {"correct": 0, "incorrect": 0}

    await ask_next(update, context)
    return AWAITING_ANSWER

async def ask_next(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    step = session[user_id]["step"]
    scenario = session[user_id]["scenario"]

    if step >= len(scenario):
        await update.message.reply_text("✅ Тренировка завершена. Введите /stop для просмотра статистики.")
        return ConversationHandler.END

    current = scenario[step]
    session[user_id]["current"] = current
    await update.message.reply_text(f"Вопрос: {current['question']}")

# === Обработка ответа пользователя ===
async def process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if user_id not in session or "current" not in session[user_id]:
        await update.message.reply_text("Сначала напишите /start.")
        return

    if session.get(user_id, {}).get("is_admin_conversation", False):
        await update.message.reply_text("Тренировка неактивна. Напишите /start для начала.")
        return

    if text.lower() == "/answer":
        last = session.get(user_id, {}).get("last")
        if last:
            await update.message.reply_text(f"Правильный ответ:\n{last['correct_answer']}")
        else:
            await update.message.reply_text("Нет правильного ответа для показа.")
        return

    if text.lower() == "/error":
        last = session.get(user_id, {}).get("last")
        if not last:
            await update.message.reply_text("Нет ответа для отправки жалобы.")
            return
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute(
            "INSERT INTO error_reports (user_id, question, answer, evaluation) VALUES (?, ?, ?, ?)",
            (user_id, last["question"], last["answer"], last["evaluation"])
        )
        conn.commit()
        conn.close()
        await update.message.reply_text("Жалоба отправлена.")
        return

    entry = session[user_id]["current"]

    evaluation_text = await evaluate_answer(entry, text, rules_data)

    evaluation_simple = "incorrect"
    lower_eval = evaluation_text.lower()
    if "полностью верно" in lower_eval or "✅" in evaluation_text:
        evaluation_simple = "correct"

    session[user_id]["last"] = {
        "question": entry["question"],
        "answer": text,
        "evaluation": evaluation_simple,
        "correct_answer": entry["expected_answer"]
    }

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        INSERT INTO logs (user_id, question, answer, evaluation, grammar_issues, correct_answer)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, entry["question"], text, evaluation_simple, "", entry["expected_answer"]))
    conn.commit()
    conn.close()

    session[user_id]["score"].setdefault(evaluation_simple, 0)
    session[user_id]["score"][evaluation_simple] += 1

    if evaluation_simple == "correct":
        await update.message.reply_text(f"✅ Верно!\n\nКомментарий ИИ:\n{evaluation_text}")
        session[user_id]["step"] += 1
        await ask_next(update, context)
    else:
        await update.message.reply_text(f"❌ Не совсем.\n\nКомментарий ИИ:\n{evaluation_text}")

# === /stop — показать статистику ===
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    score = session.get(user_id, {}).get("score", {"correct":0,"incorrect":0})
    msg = (f"📊 Статистика:\n"
           f"✅ Верных: {score.get('correct', 0)}\n"
           f"❌ Неверных: {score.get('incorrect', 0)}")
    await update.message.reply_text(msg)

# === /answer — показать последний правильный ответ ===
async def show_correct(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    last = session.get(user_id, {}).get("last")
    if not last:
        await update.message.reply_text("Нет ответа для показа.")
        return
    await update.message.reply_text(f"Правильный ответ:\n{last['correct_answer']}")

# === /error — жалоба на последний ответ ===
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

# === /admin — админ команда с паролем ===
async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите пароль администратора:")
    return ADMIN_PASS

async def admin_pass_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip()
    user_id = update.effective_user.id

    if password == ADMIN_PASSWORD:
        session.setdefault(user_id, {})
        session[user_id]["is_admin_conversation"] = True
        session[user_id]["is_admin"] = True
        await update.message.reply_text(
            "Доступ к административным командам предоставлен.\n"
            "Доступны команды:\n"
            "/mistake - показать ошибки\n"
            "/done <ID> - пометить ошибку решённой\n"
            "/exit - выйти из режима администратора"
        )
        return ADMIN_CMD
    else:
        if user_id in session:
            session[user_id]["is_admin_conversation"] = False
            session[user_id]["is_admin"] = False
        await update.message.reply_text("Неверный пароль администратора.")
        return ConversationHandler.END

async def admin_exit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in session:
        session[user_id]["is_admin_conversation"] = False
        session[user_id]["is_admin"] = False
    await update.message.reply_text("Выход из режима администратора. Напишите /start для начала тренировки.")
    return ConversationHandler.END

async def show_mistakes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not session.get(user_id, {}).get("is_admin"):
        await update.message.reply_text("Доступ запрещён.")
        return

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, question, answer, evaluation, resolved FROM mistakes WHERE resolved=0")
    rows = c.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("Нет нерешённых ошибок.")
        return

    msg = "Нерешённые ошибки:\n"
    for row in rows:
        msg += f"ID: {row[0]}\nВопрос: {row[1]}\nОтвет: {row[2]}\nОценка: {row[3]}\n\n"
    await update.message.reply_text(msg)

async def done_mistake(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not session.get(user_id, {}).get("is_admin"):
        await update.message.reply_text("Доступ запрещён.")
        return

    args = context.args
    if not args or not args[0].isdigit():
        await update.message.reply_text("Использование: /done <ID>")
        return

    mistake_id = int(args[0])
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE mistakes SET resolved=1 WHERE id=?", (mistake_id,))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"Ошибка с ID {mistake_id} помечена как решённая.")

# === /help ===
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "/auth - авторизация (ввод пароля и вход/регистрация)\n"
        "/start - начать тренировку\n"
        "/stop - остановить тренировку и показать статистику\n"
        "/answer - показать правильный ответ на последний вопрос\n"
        "/error - отправить жалобу на последний ответ\n"
        "/admin - вход в админ-панель (требуется пароль)\n"
        "/exit - выйти из админ-режима\n"
        # Команды /mistake и /done доступны только админам
    )
    await update.message.reply_text(msg)

# === Обработка неизвестных команд и сообщений ===
async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Неизвестная команда. Напишите /help для списка команд.")

# === Главное меню обработчиков ===
def main():
    global rules_data
    init_db()
    rules_data = load_rules()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    auth_conv = ConversationHandler(
        entry_points=[CommandHandler("auth", auth)],
        states={
            PASSWORD_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, password_input)],
            AUTH_CHOICE: [CallbackQueryHandler(auth_choice_handler)],
            REGISTER_LOGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_login)],
            REGISTER_PASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_pass)],
            LOGIN_LOGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_login)],
            LOGIN_PASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_pass)],
        },
        fallbacks=[],
        allow_reentry=True,
    )
    app.add_handler(auth_conv)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("answer", show_correct))
    app.add_handler(CommandHandler("error", report_error))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process))

    admin_conv = ConversationHandler(
        entry_points=[CommandHandler("admin", admin_start)],
        states={
            ADMIN_PASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_pass_input)],
            ADMIN_CMD: [
                CommandHandler("mistake", show_mistakes),
                CommandHandler("done", done_mistake),
                CommandHandler("exit", admin_exit),
                CommandHandler("cancel", admin_exit)
            ]
        },
        fallbacks=[],
        allow_reentry=True,
    )
    app.add_handler(admin_conv)

    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.COMMAND, unknown))

    app.run_polling()

if __name__ == "__main__":
    main()
