import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager

# Ensure instance folder exists
INSTANCE_FOLDER = 'instance'
if not os.path.exists(INSTANCE_FOLDER):
    os.makedirs(INSTANCE_FOLDER)

DATABASE_PATH = os.path.join(INSTANCE_FOLDER, 'memories.db')


def init_database():
    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS users
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           username
                           TEXT
                           UNIQUE
                           NOT
                           NULL,
                           password
                           TEXT
                           NOT
                           NULL,
                           created_at
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP
                       )
                       ''')

        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS memories
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           user_id
                           INTEGER
                           NOT
                           NULL,
                           memory_text
                           TEXT
                           NOT
                           NULL,
                           keywords
                           TEXT,
                           created_at
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP,
                           FOREIGN
                           KEY
                       (
                           user_id
                       ) REFERENCES users
                       (
                           id
                       ) ON DELETE CASCADE
                           )
                       ''')

        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS conversations
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           user_id
                           INTEGER,
                           user_input
                           TEXT,
                           bot_response
                           TEXT,
                           intent
                           TEXT,
                           created_at
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP,
                           FOREIGN
                           KEY
                       (
                           user_id
                       ) REFERENCES users
                       (
                           id
                       )
                           )
                       ''')

        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS medicines
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           user_id
                           INTEGER
                           NOT
                           NULL,
                           morning_medicine
                           TEXT,
                           afternoon_medicine
                           TEXT,
                           night_medicine
                           TEXT,
                           updated_at
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP,
                           FOREIGN
                           KEY
                       (
                           user_id
                       ) REFERENCES users
                       (
                           id
                       ) ON DELETE CASCADE
                           )
                       ''')

        conn.commit()
        print("✅ Database initialized!")


@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def create_user(username, password):
    with get_db_connection() as conn:
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None


def authenticate_user(username, password):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username FROM users WHERE username = ? AND password = ?", (username, password))
        return cursor.fetchone()


def save_memory(user_id, memory_text):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        keywords = ' '.join([w for w in memory_text.split() if len(w) > 2])
        cursor.execute("INSERT INTO memories (user_id, memory_text, keywords) VALUES (?, ?, ?)",
                       (user_id, memory_text, keywords[:200]))
        return cursor.lastrowid


def get_all_memories(user_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, memory_text, created_at FROM memories WHERE user_id = ? ORDER BY created_at DESC",
                       (user_id,))
        return cursor.fetchall()


def search_memories(user_id, query):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, memory_text, created_at FROM memories WHERE user_id = ? AND memory_text LIKE ? ORDER BY created_at DESC",
            (user_id, f'%{query}%'))
        return cursor.fetchall()


def log_conversation(user_id, user_input, bot_response, intent):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO conversations (user_id, user_input, bot_response, intent) VALUES (?, ?, ?, ?)",
                       (user_id, user_input, bot_response, intent))


def get_conversation_history(user_id, limit=100):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, user_input, bot_response, intent, created_at FROM conversations WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit))
        return cursor.fetchall()


def save_medicines(user_id, morning, afternoon, night):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM medicines WHERE user_id = ?", (user_id,))
        existing = cursor.fetchone()
        if existing:
            cursor.execute(
                "UPDATE medicines SET morning_medicine = ?, afternoon_medicine = ?, night_medicine = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                (morning, afternoon, night, user_id))
        else:
            cursor.execute(
                "INSERT INTO medicines (user_id, morning_medicine, afternoon_medicine, night_medicine) VALUES (?, ?, ?, ?)",
                (user_id, morning, afternoon, night))
        conn.commit()
        return True


def get_medicines(user_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT morning_medicine, afternoon_medicine, night_medicine, updated_at FROM medicines WHERE user_id = ?",
            (user_id,))
        result = cursor.fetchone()
        if result:
            return {'morning': result['morning_medicine'] or '', 'afternoon': result['afternoon_medicine'] or '', 'night': result['night_medicine'] or '', 'updated_at': result['updated_at']}
        return {'morning': '', 'afternoon': '', 'night': '', 'updated_at': None}