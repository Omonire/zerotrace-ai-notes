import os
import hashlib
import json
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


def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"success": False, "message": "Not signed in"}), 401
        return f(*args, **kwargs)
    return decorated


def search_notes(db, search, user_id):
    if search:
        return db.execute(
            "SELECT * FROM notes WHERE user_id = ? AND (title LIKE ? OR content LIKE ?) ORDER BY created_at DESC",
            (user_id, f"%{search}%", f"%{search}%")
        ).fetchall()
    return db.execute("SELECT * FROM notes WHERE user_id = ? ORDER BY created_at DESC", (user_id,)).fetchall()


def get_ai_usage_today(db, user_id):
    row = db.execute(
        "SELECT COUNT(*) as count FROM ai_usage WHERE user_id = ? AND DATE(created_at) = DATE('now')",
        (user_id,)
    ).fetchone()
    return row["count"]


# ─── Pages ──────────────────────────────────────────────────────

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
    if "user_id" not in session:
        return redirect("/signin")
    search = request.args.get("search", "").strip()
    db = get_db()
    try:
        notes = search_notes(db, search, session["user_id"])
    finally:
        db.close()
    return render_template("demo_index.html", notes=notes, search=search, username=session.get("username"))


@app.route("/api/notes", methods=["GET"])
@login_required
def get_notes():
    search = request.args.get("search", "").strip()
    db = get_db()
    try:
        notes = search_notes(db, search, session["user_id"])
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
@login_required
def get_note(note_id):
    db = get_db()
    try:
        note = db.execute("SELECT * FROM notes WHERE id = ? AND user_id = ?", (note_id, session["user_id"])).fetchone()
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
@login_required
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
            "INSERT INTO notes (title, content, user_id) VALUES (?, ?, ?)",
            (title, content, session["user_id"])
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
@login_required
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
        existing = db.execute("SELECT * FROM notes WHERE id = ? AND user_id = ?", (note_id, session["user_id"])).fetchone()
        if not existing:
            return jsonify({"success": False, "message": "Note not found"}), 404

        db.execute(
            "UPDATE notes SET title = ?, content = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ?",
            (title, content, note_id, session["user_id"])
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
@login_required
def delete_note(note_id):
    db = get_db()
    try:
        existing = db.execute("SELECT * FROM notes WHERE id = ? AND user_id = ?", (note_id, session["user_id"])).fetchone()
        if not existing:
            return jsonify({"success": False, "message": "Note not found"}), 404

        db.execute("DELETE FROM notes WHERE id = ? AND user_id = ?", (note_id, session["user_id"]))
        db.commit()
    finally:
        db.close()

    return jsonify({"success": True, "message": "Note deleted successfully"})


# ─── AI Routes ──────────────────────────────────────────────────

AI_ACTIONS = {
    "summarize": "Summarize the following note concisely. Keep the key points and main ideas. Output only the summary, no preamble.",
    "expand": "Expand the following note with more detail, context, and depth. Keep the original meaning. Output only the expanded text.",
    "rewrite": "Rewrite the following note to be clearer and more polished. Keep the meaning but improve flow and readability. Output only the rewritten text.",
}


@app.route("/api/ai/<action>", methods=["POST"])
@login_required
def ai_action(action):
    if action not in AI_ACTIONS:
        return jsonify({"success": False, "message": "Invalid action. Use: summarize, expand, rewrite"}), 400

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No data received"}), 400

    content = data.get("content", "").strip()
    if not content:
        return jsonify({"success": False, "message": "No content to process"}), 400

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return jsonify({"success": False, "message": "AI not configured. Set OPENAI_API_KEY in .env"}), 503

    db = get_db()
    try:
        usage = get_ai_usage_today(db, session["user_id"])
        if usage >= 10:
            return jsonify({"success": False, "message": "Daily AI limit reached (10/day). Try again tomorrow."}), 429
    finally:
        db.close()

    try:
        import urllib.request

        system_prompt = AI_ACTIONS[action]
        payload = json.dumps({
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content}
            ],
            "max_tokens": 2000,
            "temperature": 0.7
        })

        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=payload.encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())

        result_text = result["choices"][0]["message"]["content"].strip()
        tokens = result.get("usage", {}).get("total_tokens", 0)

        db = get_db()
        try:
            db.execute(
                "INSERT INTO ai_usage (user_id, action, tokens_used) VALUES (?, ?, ?)",
                (session["user_id"], action, tokens)
            )
            db.commit()
        finally:
            db.close()

        return jsonify({
            "success": True,
            "result": result_text,
            "action": action,
            "tokens_used": tokens,
            "remaining_today": 9 - usage
        })

    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        try:
            error_data = json.loads(error_body)
            msg = error_data.get("error", {}).get("message", "AI request failed")
        except Exception:
            msg = "AI request failed"
        return jsonify({"success": False, "message": msg}), 502
    except Exception as e:
        return jsonify({"success": False, "message": "AI service unavailable"}), 502


@app.route("/api/ai/usage", methods=["GET"])
@login_required
def ai_usage():
    db = get_db()
    try:
        usage = get_ai_usage_today(db, session["user_id"])
    finally:
        db.close()
    return jsonify({"used": usage, "limit": 10, "remaining": 10 - usage})


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true")
