import hmac
import hashlib
import os
import sqlite3

from werkzeug.security import check_password_hash, generate_password_hash

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

Dir_name = os.path.abspath(__file__)
path_dir_name = os.path.dirname(Dir_name)
DATABASE = os.environ.get("DATABASE_PATH") or os.path.join(path_dir_name, 'AI_Notes.db')


def hash_password(password):
    return generate_password_hash(password)


def verify_password(password, stored):
    if not stored:
        return False
    try:
        if check_password_hash(stored, password):
            return True
    except (ValueError, TypeError):
        pass
    legacy = hashlib.sha256(password.encode()).hexdigest()
    return hmac.compare_digest(stored, legacy)


def needs_rehash(stored):
    return bool(stored) and not stored.startswith(("pbkdf2:", "scrypt:"))


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
            content_format TEXT DEFAULT 'plain',
            user_id INTEGER DEFAULT NULL,
            is_pinned INTEGER DEFAULT 0,
            is_deleted INTEGER DEFAULT 0,
            deleted_at TIMESTAMP DEFAULT NULL,
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
            email_verified INTEGER DEFAULT 0,
            verification_token TEXT DEFAULT NULL,
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
    db.execute("""
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            color TEXT DEFAULT '#7c5cff',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(name, user_id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS note_tags (
            note_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            PRIMARY KEY (note_id, tag_id),
            FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS login_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_address TEXT NOT NULL,
            username TEXT,
            attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db.commit()

    # Migrations
    cols = [r[1] for r in db.execute("PRAGMA table_info(notes)").fetchall()]
    migrations = {
        "user_id": "ALTER TABLE notes ADD COLUMN user_id INTEGER DEFAULT NULL",
        "content_format": "ALTER TABLE notes ADD COLUMN content_format TEXT DEFAULT 'plain'",
        "is_pinned": "ALTER TABLE notes ADD COLUMN is_pinned INTEGER DEFAULT 0",
        "is_deleted": "ALTER TABLE notes ADD COLUMN is_deleted INTEGER DEFAULT 0",
        "deleted_at": "ALTER TABLE notes ADD COLUMN deleted_at TIMESTAMP DEFAULT NULL",
    }
    for col, sql in migrations.items():
        if col not in cols:
            db.execute(sql)
            db.commit()

    user_cols = [r[1] for r in db.execute("PRAGMA table_info(users)").fetchall()]
    user_migrations = {
        "email_verified": "ALTER TABLE users ADD COLUMN email_verified INTEGER DEFAULT 0",
        "verification_token": "ALTER TABLE users ADD COLUMN verification_token TEXT DEFAULT NULL",
    }
    for col, sql in user_migrations.items():
        if col not in user_cols:
            db.execute(sql)
            db.commit()

    db.close()
