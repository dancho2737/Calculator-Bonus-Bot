import aiosqlite
from datetime import datetime

DB_PATH = "bot_responses.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS operator_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                question TEXT,
                operator_answer TEXT,
                evaluation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                positives TEXT,
                negatives TEXT,
                grammar_errors TEXT,
                total_score INTEGER
            )
        ''')
        await db.commit()

async def save_response(user_id: int, username: str, question: str, operator_answer: str,
                        positives: str, negatives: str, grammar_errors: str, total_score: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            INSERT INTO operator_responses (
                user_id, username, question, operator_answer, evaluation_date,
                positives, negatives, grammar_errors, total_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, username, question, operator_answer, datetime.utcnow(),
              positives, negatives, grammar_errors, total_score))
        await db.commit()

async def fetch_all_responses():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT * FROM operator_responses ORDER BY evaluation_date DESC')
        rows = await cursor.fetchall()
        return rows

