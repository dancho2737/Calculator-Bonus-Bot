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

# === Загрузка правил из папки rules ===
def load_rules():
    rules_data = {}
    if not os.path.exists(RULES_FOLDER):
        logger.warning(f"Папка с правилами {RULES_FOLDER} не найдена")
        return rules_data
    for filename in os.listdir(RULES_FOLDER):
        if filename.endswith(".txt"):
            path = os.path.join(RULES_FOLDER, filename)
            with open(path, encoding="utf-8") as f:
                content = f.read()
                key = os.path.splitext(filename)[0].lower()
                rules_data[key] = content
    logger.info(f"Загружено правил из {len(rules_data)} файлов из {RULES_FOLDER}")
    return rules_data

# === DATABASE INIT ===
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                login TEXT UNIQUE,
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

# === Загрузка сценариев ===
def load_scenarios():
    with open(SCENARIO_FILE, encoding='utf-8') as f:
        data = json.load(f)
    random.shuffle(data)
    return data

# === Оценка ответов ИИ ===
async def evaluate_answer(entry, user_answer):
    question = entry["question"]
    expected_answer = entry["expected_answer"]

    prompt = TRAINING_PROMPT.format(question=question, expected_answer=expected_answer)
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

# Обработка кнопок регистрации/входа
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
    else:
        await query.edit_message_text("Неизвестный выбор. Начните заново с /auth.")
        return ConversationHandler.END

# Регистрация — ввод логина
async def register_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    login = update.message.text.strip()
    if not login:
        await update.message.reply_text("Логин не может быть пустым. Введите логин:")
        return REGISTER_LOGIN

    context.user_data['register_login'] = login
    await update.message.reply_text("Введите пароль для регистрации:")
    return REGISTER_PASS

# Регистрация — ввод пароля
async def register_pass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip()
    login = context.user_data.get('register_login')
    user_id = update.effective_user.id
    username = update.effective_user.username or ""

    if not password:
        await update.message.reply_text("Пароль не может быть пустым. Введите пароль:")
        return REGISTER_PASS

    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE login=?", (login,))
            if c.fetchone():
                await update.message.reply_text("❌ Такой логин уже существует. Введите другой логин или начните заново через /auth.")
                return ConversationHandler.END

            c.execute("INSERT INTO users (user_id, username, login, password) VALUES (?, ?, ?, ?)",
                      (user_id, username, login, password))
            conn.commit()
    except Exception as e:
        logger.error(f"Ошибка регистрации: {e}")
        await update.message.reply_text("Ошибка при регистрации. Попробуйте позже.")
        return ConversationHandler.END

    session[user_id] = {"authenticated": True, "login": login}
    await update.message.reply_text("✅ Регистрация успешна! Напишите /start для начала тренировки.")
    return ConversationHandler.END

# Вход — ввод логина
async def login_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    login = update.message.text.strip()
    if not login:
        await update.message.reply_text("Логин не может быть пустым. Введите логин:")
        return LOGIN_LOGIN

    context.user_data['login_login'] = login
    await update.message.reply_text("Введите пароль для входа:")
    return LOGIN_PASS

# Вход — ввод пароля
async def login_pass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip()
    login = context.user_data.get('login_login')
    user_id = update.effective_user.id

    if not password:
        await update.message.reply_text("Пароль не может быть пустым. Введите пароль:")
        return LOGIN_PASS

    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE login=? AND password=?", (login, password))
            user = c.fetchone()
    except Exception as e:
        logger.error(f"Ошибка при входе: {e}")
        await update.message.reply_text("Ошибка при входе. Попробуйте позже.")
        return ConversationHandler.END

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

    return await ask_next(update, context)

async def ask_next(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    step = session[user_id].get("step", 0)
    scenario = session[user_id].get("scenario", [])

    if step >= len(scenario):
        await update.message.reply_text("✅ Тренировка завершена. Введите /stop для просмотра статистики.")
        return ConversationHandler.END

    current = scenario[step]
    session[user_id]["current"] = current
    await update.message.reply_text(f"Вопрос: {current['question']}")
    return AWAITING_ANSWER

# === Обработка ответа пользователя и команд во время тренировки ===
async def process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if user_id not in session or "current" not in session[user_id]:
        await update.message.reply_text("Сначала напишите /start.")
        return

    if session.get(user_id, {}).get("is_admin_conversation", False):
        await update.message.reply_text("Тренировка неактивна. Напишите /start для начала.")
        return

    # Обработка команд
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
        try:
            with sqlite3.connect(DB_FILE) as conn:
                c = conn.cursor()
                c.execute(
                    "INSERT INTO error_reports (user_id, question, answer, evaluation) VALUES (?, ?, ?, ?)",
                    (user_id, last["question"], last["answer"], last["evaluation"])
                )
                conn.commit()
            await update.message.reply_text("Жалоба отправлена.")
        except Exception as e:
            logger.error(f"Ошибка при отправке жалобы: {e}")
            await update.message.reply_text("Ошибка при отправке жалобы. Попробуйте позже.")
        return

    entry = session[user_id]["current"]
    evaluation_text = await evaluate_answer(entry, text)

    evaluation_simple = "incorrect"
    lower_eval = evaluation_text.lower()
    if "полностью верно" in lower_eval or "✅" in evaluation_text or "верно" in lower_eval:
        evaluation_simple = "correct"

    session[user_id]["last"] = {
        "question": entry["question"],
        "answer": text,
        "evaluation": evaluation_simple,
        "correct_answer": entry["expected_answer"]
    }

    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO logs (user_id, question, answer, evaluation, grammar_issues, correct_answer)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, entry["question"], text, evaluation_simple, "", entry["expected_answer"]))
            conn.commit()
    except Exception as e:
        logger.error(f"Ошибка при записи лога: {e}")

    # Обновление счёта
    if "score" not in session[user_id]:
        session[user_id]["score"] = {"correct": 0, "incorrect": 0}
    session[user_id]["score"].setdefault("correct", 0)
    session[user_id]["score"].setdefault("incorrect", 0)
    session[user_id]["score"][evaluation_simple] += 1

    if evaluation_simple == "correct":
        await update.message.reply_text(f"✅ Верно!\n\nКомментарий ИИ:\n{evaluation_text}")
        session[user_id]["step"] += 1
        return await ask_next(update, context)
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

    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute("INSERT INTO error_reports (user_id, question, answer, evaluation) VALUES (?, ?, ?, ?)",
                      (user_id, last["question"], last["answer"], last["evaluation"]))
            conn.commit()
        await update.message.reply_text("Жалоба отправлена.")
    except Exception as e:
        logger.error(f"Ошибка при отправке жалобы: {e}")
        await update.message.reply_text("Ошибка при отправке жалобы. Попробуйте позже.")

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

# Команда выхода из админ-режима
async def admin_exit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in session:
        session[user_id]["is_admin_conversation"] = False
        session[user_id]["is_admin"] = False
    await update.message.reply_text("Выход из режима администратора. Напишите /start для начала тренировки.")
    return ConversationHandler.END

# Показать ошибки /mistake
async def show_mistakes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not session.get(user_id, {}).get("is_admin"):
        await update.message.reply_text("Доступ запрещён.")
        return

    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute("SELECT id, question, answer, evaluation, resolved FROM mistakes WHERE resolved=0")
            rows = c.fetchall()
    except Exception as e:
        logger.error(f"Ошибка при получении ошибок: {e}")
        await update.message.reply_text("Ошибка при получении данных.")
        return

    if not rows:
        await update.message.reply_text("Нет нерешённых ошибок.")
        return

    msg = "Нерешённые ошибки:\n"
    for row in rows:
        msg += f"ID: {row[0]}\nВопрос: {row[1]}\nОтвет: {row[2]}\nОценка: {row[3]}\n\n"
    await update.message.reply_text(msg)

# Пометить ошибку решённой /done ID
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
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute("UPDATE mistakes SET resolved=1 WHERE id=?", (mistake_id,))
            conn.commit()
        await update.message.reply_text(f"Ошибка с ID {mistake_id} помечена как решённая.")
    except Exception as e:
        logger.error(f"Ошибка при обновлении ошибки: {e}")
        await update.message.reply_text("Ошибка при обновлении записи. Попробуйте позже.")

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

# === Обработчик для входа в админ режим в любой момент ===
async def handle_admin_password_anytime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    if text == ADMIN_PASSWORD:
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
    return  # Иначе игнорируем

# === Главное меню обработчиков ===
def main():
    init_db()
    rules = load_rules()  # можно сохранить, если будешь использовать в обработчиках

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Конверсация авторизации
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

    # Тренировка
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("answer", show_correct))
    app.add_handler(CommandHandler("error", report_error))

    # Вход в админ режим в любой момент (текст)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_password_anytime), group=1)

    # Обработка тренировочных ответов
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process), group=2)

    # Админ панель
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

    # Помощь и неизвестные команды
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.COMMAND, unknown))

    app.run_polling()

if __name__ == "__main__":
    main()
