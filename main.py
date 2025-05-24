from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import math
import os

TOKEN = 8104597347:AAGEkQ8ABc1XF57fC9ObKVPlqW7twI3Ddds

def safe_eval(expr):
    try:
        allowed_names = {k: v for k, v in math.__dict__.items() if not k.startswith("__")}
        result = eval(expr, {"__builtins__": {}}, allowed_names)
        return result
    except Exception as e:
        return f"Ошибка: {e}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Отправь /calc 2 + 2, и я посчитаю!")

async def calc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    expr = ' '.join(context.args)
    if not expr:
        await update.message.reply_text("Пример: /calc 2 + 2")
        return
    result = safe_eval(expr)
    await update.message.reply_text(f"Результат: {result}")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("calc", calc))
    app.run_polling()
  
