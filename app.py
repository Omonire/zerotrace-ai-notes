import os
import hashlib
from flask import Flask, render_template, request, redirect, jsonify, session
from database import init_db, get_db

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")

init_db()

from auth import auth_bp
app.register_blueprint(auth_bp)


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def search_notes(db, search):
    if search:
        return db.execute(
            "SELECT * FROM notes WHERE title LIKE ? OR content LIKE ? ORDER BY created_at DESC",
            (f"%{search}%", f"%{search}%")
        ).fetchall()
    return db.execute("SELECT * FROM notes ORDER BY created_at DESC").fetchall()


@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/waitlist", methods=["GET"])
def waitlist_page():
    return render_template("waitlist.html")


@app.route("/api/waitlist", methods=["POST"])
def join_waitlist():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No data received"}), 400

    name = data.get("name", "").strip()
    email = data.get("email", "").strip()

    if not name or not email:
        return jsonify({"success": False, "message": "Name and email are required"}), 400

    if "@" not in email or "." not in email:
        return jsonify({"success": False, "message": "Please enter a valid email"}), 400

    db = get_db()
    try:
        existing = db.execute("SELECT id FROM waitlist WHERE email = ?", (email,)).fetchone()
        if existing:
            return jsonify({"success": False, "message": "You're already on the waitlist"}), 409

        db.execute("INSERT INTO waitlist (name, email) VALUES (?, ?)", (name, email))
        db.commit()
        return jsonify({"success": True, "message": "You're on the waitlist!"}), 201
    finally:
        db.close()


# ─── Auth Routes ────────────────────────────────────────────────

@app.route("/signup", methods=["GET"])
def signup_page():
    if "user_id" in session:
        return redirect("/app")
    return render_template("signup.html")


@app.route("/api/signup", methods=["POST"])
def signup():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No data received"}), 400

    username = data.get("username", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    if not username or not email or not password:
        return jsonify({"success": False, "message": "All fields are required"}), 400

    if len(username) < 3:
        return jsonify({"success": False, "message": "Username must be at least 3 characters"}), 400

    if len(password) < 6:
        return jsonify({"success": False, "message": "Password must be at least 6 characters"}), 400

    if "@" not in email or "." not in email:
        return jsonify({"success": False, "message": "Please enter a valid email"}), 400

    db = get_db()
    try:
        existing = db.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email)).fetchone()
        if existing:
            return jsonify({"success": False, "message": "Username or email already taken"}), 409

        db.execute(
            "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
            (username, email, hash_password(password))
        )
        db.commit()
        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["is_admin"] = user["is_admin"]
        return jsonify({"success": True, "message": "Account created"}), 201
    finally:
        db.close()


@app.route("/signin", methods=["GET"])
def signin_page():
    if "user_id" in session:
        return redirect("/app")
    return render_template("signin.html")


@app.route("/api/signin", methods=["POST"])
def signin():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No data received"}), 400

    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({"success": False, "message": "Username and password are required"}), 400

    db = get_db()
    try:
        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if not user or user["password"] != hash_password(password):
            return jsonify({"success": False, "message": "Invalid username or password"}), 401

        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["is_admin"] = user["is_admin"]
        return jsonify({"success": True, "message": "Signed in"})
    finally:
        db.close()


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ─── Superadmin ─────────────────────────────────────────────────

@app.route("/superadmin/dashboard")
def superadmin_dashboard():
    if not session.get("is_admin"):
        return redirect("/signin")

    db = get_db()
    try:
        total_users = db.execute("SELECT COUNT(*) as count FROM users").fetchone()["count"]
        total_notes = db.execute("SELECT COUNT(*) as count FROM notes").fetchone()["count"]
        total_waitlist = db.execute("SELECT COUNT(*) as count FROM waitlist").fetchone()["count"]

        users = db.execute("SELECT id, username, email, is_admin, created_at FROM users ORDER BY created_at DESC").fetchall()
        recent_notes = db.execute("SELECT id, title, created_at FROM notes ORDER BY created_at DESC LIMIT 10").fetchall()

        users_per_day = db.execute("""
            SELECT DATE(created_at) as day, COUNT(*) as count
            FROM users
            GROUP BY DATE(created_at)
            ORDER BY day DESC
            LIMIT 30
        """).fetchall()

        notes_per_day = db.execute("""
            SELECT DATE(created_at) as day, COUNT(*) as count
            FROM notes
            GROUP BY DATE(created_at)
            ORDER BY day DESC
            LIMIT 30
        """).fetchall()

        waitlist_per_day = db.execute("""
            SELECT DATE(created_at) as day, COUNT(*) as count
            FROM waitlist
            GROUP BY DATE(created_at)
            ORDER BY day DESC
            LIMIT 30
        """).fetchall()
    finally:
        db.close()

    return render_template("superadmin.html",
        total_users=total_users,
        total_notes=total_notes,
        total_waitlist=total_waitlist,
        users=users,
        recent_notes=recent_notes,
        users_per_day=users_per_day,
        notes_per_day=notes_per_day,
        waitlist_per_day=waitlist_per_day
    )


@app.route("/api/admin/users", methods=["GET"])
def admin_get_users():
    if not session.get("is_admin"):
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    db = get_db()
    try:
        users = db.execute("SELECT id, username, email, is_admin, created_at FROM users ORDER BY created_at DESC").fetchall()
    finally:
        db.close()

    return jsonify([{
        "id": u["id"],
        "username": u["username"],
        "email": u["email"],
        "is_admin": bool(u["is_admin"]),
        "created_at": u["created_at"]
    } for u in users])


# ─── App Routes ─────────────────────────────────────────────────

@app.route("/app")
def home():
    search = request.args.get("search", "").strip()
    db = get_db()
    try:
        notes = search_notes(db, search)
    finally:
        db.close()
    return render_template("demo_index.html", notes=notes, search=search)


@app.route("/api/notes", methods=["GET"])
def get_notes():
    search = request.args.get("search", "").strip()
    db = get_db()
    try:
        notes = search_notes(db, search)
    finally:
        db.close()
    return jsonify([{
        "id": row["id"],
        "title": row["title"],
        "content": row["content"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"]
    } for row in notes])


@app.route("/api/notes/<int:note_id>", methods=["GET"])
def get_note(note_id):
    db = get_db()
    try:
        note = db.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
        if not note:
            return jsonify({"success": False, "message": "Note not found"}), 404
        return jsonify({
            "success": True,
            "note": {
                "id": note["id"],
                "title": note["title"],
                "content": note["content"],
                "created_at": note["created_at"],
                "updated_at": note["updated_at"]
            }
        })
    finally:
        db.close()


@app.route("/api/notes", methods=["POST"])
def create_note():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No data received or invalid JSON"}), 400

    title = data.get("title", "").strip()
    content = data.get("content", "").strip()

    if not title or not content:
        return jsonify({"success": False, "message": "Title and content are required"}), 400

    db = get_db()
    try:
        note_id = db.execute(
            "INSERT INTO notes (title, content) VALUES (?, ?)", (title, content)
        ).lastrowid
        db.commit()
        note = db.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
    finally:
        db.close()

    return jsonify({
        "success": True,
        "message": "Note created successfully",
        "note": {
            "id": note["id"],
            "title": note["title"],
            "content": note["content"],
            "created_at": note["created_at"],
            "updated_at": note["updated_at"]
        }
    }), 201


@app.route("/api/notes/<int:note_id>", methods=["PUT"])
def update_note(note_id):
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No data received or invalid JSON"}), 400

    title = data.get("title", "").strip()
    content = data.get("content", "").strip()

    if not title or not content:
        return jsonify({"success": False, "message": "Title and content are required"}), 400

    db = get_db()
    try:
        existing = db.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
        if not existing:
            return jsonify({"success": False, "message": "Note not found"}), 404

        db.execute(
            "UPDATE notes SET title = ?, content = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (title, content, note_id)
        )
        db.commit()
        note = db.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
    finally:
        db.close()

    return jsonify({
        "success": True,
        "message": "Note updated successfully",
        "note": {
            "id": note["id"],
            "title": note["title"],
            "content": note["content"],
            "created_at": note["created_at"],
            "updated_at": note["updated_at"]
        }
    })


@app.route("/api/notes/<int:note_id>", methods=["DELETE"])
def delete_note(note_id):
    db = get_db()
    try:
        existing = db.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
        if not existing:
            return jsonify({"success": False, "message": "Note not found"}), 404

        db.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        db.commit()
    finally:
        db.close()

    return jsonify({"success": True, "message": "Note deleted successfully"})


@app.route("/notes/save", methods=["POST"])
def save_note():
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()

    if not title or not content:
        return redirect("/app?error=Title+and+content+are+required")

    db = get_db()
    try:
        db.execute("INSERT INTO notes (title, content) VALUES (?, ?)", (title, content))
        db.commit()
    finally:
        db.close()

    return redirect("/app")


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true")
