import sqlite3
import os
import hashlib

Dir_name = os.path.abspath(__file__)
path_dir_name = os.path.dirname(Dir_name)
DATABASE = os.path.join(path_dir_name, 'AI_Notes.db')


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    db = get_db()
    db.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            user_id INTEGER DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS waitlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS ai_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            tokens_used INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    db.commit()

    # Migrate: add user_id to notes if missing
    cols = [r[1] for r in db.execute("PRAGMA table_info(notes)").fetchall()]
    if "user_id" not in cols:
        db.execute("ALTER TABLE notes ADD COLUMN user_id INTEGER DEFAULT NULL")
        db.commit()

    # Auto-seed default admin
    admin = db.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()
    if not admin:
        db.execute(
            "INSERT INTO users (username, email, password, is_admin) VALUES (?, ?, ?, 1)",
            ("admin", "admin@zerotrace.com", hash_password("admin123"))
        )
        db.commit()

    db.close()
