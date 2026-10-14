"""Create or update the local development admin user."""

from database import get_db, hash_password, init_db, verify_password

USERNAME = "admin"
PASSWORD = "Password123."
EMAIL = "admin@example.com"


def seed_admin() -> None:
    init_db()
    db = get_db()
    try:
        existing = db.execute(
            "SELECT id FROM users WHERE username = ?",
            (USERNAME,),
        ).fetchone()

        if existing:
            db.execute(
                """
                UPDATE users
                SET email = ?, password = ?, is_admin = 1, email_verified = 1
                WHERE id = ?
                """,
                (EMAIL, hash_password(PASSWORD), existing["id"]),
            )
            action = "updated"
        else:
            db.execute(
                """
                INSERT INTO users
                    (username, email, password, is_admin, email_verified)
                VALUES (?, ?, ?, 1, 1)
                """,
                (USERNAME, EMAIL, hash_password(PASSWORD)),
            )
            action = "created"

        db.commit()

        saved = db.execute(
            "SELECT password, is_admin FROM users WHERE username = ?",
            (USERNAME,),
        ).fetchone()
        if not saved or not saved["is_admin"] or not verify_password(PASSWORD, saved["password"]):
            raise RuntimeError("Admin seed verification failed")

        print(f"Admin user {action}: {USERNAME}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_admin()
