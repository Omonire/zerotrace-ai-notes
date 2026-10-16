import os
import secrets
import time
from flask import Flask, render_template, request, redirect, jsonify, session
from database import init_db, get_db, hash_password, needs_rehash, verify_password

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")

SUPERADMIN_USERNAME = os.environ.get("SUPERADMIN_USERNAME", "superadmin")
SUPERADMIN_PASSWORD = os.environ.get("SUPERADMIN_PASSWORD", "")

def register_app_routers(flask_app):
    """Initialize the database and register all application blueprints."""
    init_db()

    from auth import auth_bp
    from fscss import fscss_bp
    from Bot import bot_bp
    for blueprint in (auth_bp, fscss_bp, bot_bp):
        if blueprint.name not in flask_app.blueprints:
            flask_app.register_blueprint(blueprint)


register_app_routers(app)


def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"success": False, "message": "Not signed in"}), 401
        return f(*args, **kwargs)
    return decorated


# ─── Rate Limiting ──────────────────────────────────────────

LOGIN_ATTEMPTS = {}
RATE_LIMIT_WINDOW = 900
RATE_LIMIT_MAX = 5

def check_rate_limit(ip):
    now = time.time()
    if ip not in LOGIN_ATTEMPTS:
        LOGIN_ATTEMPTS[ip] = []
    LOGIN_ATTEMPTS[ip] = [t for t in LOGIN_ATTEMPTS[ip] if now - t < RATE_LIMIT_WINDOW]
    if len(LOGIN_ATTEMPTS[ip]) >= RATE_LIMIT_MAX:
        return False
    return True

def record_login_attempt(ip):
    now = time.time()
    if ip not in LOGIN_ATTEMPTS:
        LOGIN_ATTEMPTS[ip] = []
    LOGIN_ATTEMPTS[ip].append(now)


SORT_ORDERS = {
    "newest": "created_at DESC",
    "oldest": "created_at ASC",
    "alpha": "title ASC",
    "alpha_desc": "title DESC",
}


def get_notes_query(db, user_id, search="", sort="newest", tag_id=None, include_deleted=False):
    conditions = ["user_id = ?"]
    params = [user_id]

    if not include_deleted:
        conditions.append("is_deleted = 0")

    if search:
        conditions.append("(title LIKE ? OR content LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])

    if tag_id:
        conditions.append("id IN (SELECT note_id FROM note_tags WHERE tag_id = ?)")
        params.append(tag_id)

    where = " AND ".join(conditions)
    order = SORT_ORDERS.get(sort, "created_at DESC")

    return db.execute(
        f"SELECT * FROM notes WHERE {where} ORDER BY is_pinned DESC, {order}",
        params
    ).fetchall()


def get_note_tags(db, note_id):
    tags = db.execute("""
        SELECT t.id, t.name, t.color FROM tags t
        JOIN note_tags nt ON t.id = nt.tag_id
        WHERE nt.note_id = ?
    """, (note_id,)).fetchall()
    return [{"id": t["id"], "name": t["name"], "color": t["color"]} for t in tags]


def get_ai_usage_today(db, user_id):
    row = db.execute(
        "SELECT COUNT(*) as count FROM ai_usage WHERE user_id = ? AND DATE(created_at) = DATE('now')",
        (user_id,)
    ).fetchone()
    return row["count"]


# ─── Pages ──────────────────────────────────────────────────────

@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"}), 200


@app.route("/")
def landing():
    return render_template("landing.html", signed_in="user_id" in session)


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

    ip = request.remote_addr
    if not check_rate_limit(ip):
        return jsonify({"success": False, "message": "Too many attempts. Try again later."}), 429

    db = get_db()
    try:
        existing = db.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email)).fetchone()
        if existing:
            return jsonify({"success": False, "message": "Username or email already taken"}), 409

        token = secrets.token_urlsafe(32)
        db.execute(
            "INSERT INTO users (username, email, password, verification_token) VALUES (?, ?, ?, ?)",
            (username, email, hash_password(password), token)
        )
        db.commit()
        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        return jsonify({"success": True, "message": "Account created", "verification_token": token}), 201
    finally:
        db.close()


@app.route("/api/verify-email", methods=["POST"])
def verify_email():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No data received"}), 400

    token = data.get("token", "").strip()
    if not token:
        return jsonify({"success": False, "message": "Verification token required"}), 400

    db = get_db()
    try:
        user = db.execute("SELECT * FROM users WHERE verification_token = ?", (token,)).fetchone()
        if not user:
            return jsonify({"success": False, "message": "Invalid verification token"}), 400

        db.execute("UPDATE users SET email_verified = 1, verification_token = NULL WHERE id = ?", (user["id"],))
        db.commit()
        return jsonify({"success": True, "message": "Email verified!"})
    finally:
        db.close()


@app.route("/verify", methods=["GET"])
def verify_page():
    token = request.args.get("token", "")
    return render_template("verify.html", token=token)


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

    ip = request.remote_addr
    if not check_rate_limit(ip):
        return jsonify({"success": False, "message": "Too many attempts. Try again in 15 minutes."}), 429

    db = get_db()
    try:
        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if not user or not verify_password(password, user["password"]):
            record_login_attempt(ip)
            return jsonify({"success": False, "message": "Invalid username or password"}), 401

        if needs_rehash(user["password"]):
            db.execute("UPDATE users SET password = ? WHERE id = ?", (hash_password(password), user["id"]))
            db.commit()

        record_login_attempt(ip)
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        return jsonify({"success": True, "message": "Signed in", "email_verified": bool(user["email_verified"])})
    finally:
        db.close()


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ─── Superadmin ─────────────────────────────────────────────────

def superadmin_configured():
    return bool(SUPERADMIN_PASSWORD)


def is_superadmin():
    return session.get("is_superadmin") is True


def superadmin_dashboard_context():
    db = get_db()
    try:
        total_users = db.execute("SELECT COUNT(*) as count FROM users").fetchone()["count"]
        total_notes = db.execute("SELECT COUNT(*) as count FROM notes").fetchone()["count"]
        total_waitlist = db.execute("SELECT COUNT(*) as count FROM waitlist").fetchone()["count"]

        users = db.execute("SELECT id, username, email, created_at FROM users ORDER BY created_at DESC").fetchall()
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

    return {
        "total_users": total_users,
        "total_notes": total_notes,
        "total_waitlist": total_waitlist,
        "users": users,
        "recent_notes": recent_notes,
        "users_per_day": users_per_day,
        "notes_per_day": notes_per_day,
        "waitlist_per_day": waitlist_per_day,
    }


@app.route("/superadmin")
def superadmin():
    if not is_superadmin():
        return render_template("superadmin_login.html", configured=superadmin_configured())
    return render_template("superadmin.html", **superadmin_dashboard_context())


@app.route("/superadmin/login", methods=["POST"])
def superadmin_login():
    if not superadmin_configured():
        return jsonify({"success": False, "message": "Superadmin is not configured. Set SUPERADMIN_PASSWORD in .env"}), 503

    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    ip = request.remote_addr
    if not check_rate_limit(ip):
        return jsonify({"success": False, "message": "Too many attempts. Try again in 15 minutes."}), 429

    if not (secrets.compare_digest(username, SUPERADMIN_USERNAME) and secrets.compare_digest(password, SUPERADMIN_PASSWORD)):
        record_login_attempt(ip)
        return jsonify({"success": False, "message": "Invalid superadmin credentials"}), 401

    session["is_superadmin"] = True
    return jsonify({"success": True, "message": "Signed in as superadmin"})


@app.route("/superadmin/logout")
def superadmin_logout():
    session.pop("is_superadmin", None)
    return redirect("/superadmin")


@app.route("/api/superadmin/users", methods=["GET"])
def superadmin_get_users():
    if not is_superadmin():
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    db = get_db()
    try:
        users = db.execute("SELECT id, username, email, created_at FROM users ORDER BY created_at DESC").fetchall()
    finally:
        db.close()

    return jsonify([{
        "id": u["id"],
        "username": u["username"],
        "email": u["email"],
        "created_at": u["created_at"]
    } for u in users])


# ─── App Routes ─────────────────────────────────────────────────

@app.route("/app")
def home():
    if "user_id" not in session:
        return redirect("/signin")
    search = request.args.get("search", "").strip()
    sort = request.args.get("sort", "newest").strip()
    tag = request.args.get("tag", "").strip()
    db = get_db()
    try:
        tag_id = int(tag) if tag.isdigit() else None
        notes = get_notes_query(db, session["user_id"], search, sort, tag_id)
        tags = db.execute("SELECT * FROM tags WHERE user_id = ? ORDER BY name", (session["user_id"],)).fetchall()
    finally:
        db.close()
    return render_template("demo_index.html", notes=notes, search=search, sort=sort, tags=tags, username=session.get("username"))


@app.route("/trash")
def trash_page():
    if "user_id" not in session:
        return redirect("/signin")
    db = get_db()
    try:
        notes = db.execute(
            "SELECT * FROM notes WHERE user_id = ? AND is_deleted = 1 ORDER BY deleted_at DESC",
            (session["user_id"],)
        ).fetchall()
    finally:
        db.close()
    return render_template("trash.html", notes=notes, username=session.get("username"))


@app.route("/api/notes", methods=["GET"])
@login_required
def get_notes():
    search = request.args.get("search", "").strip()
    sort = request.args.get("sort", "newest").strip()
    tag = request.args.get("tag", "").strip()
    db = get_db()
    try:
        tag_id = int(tag) if tag.isdigit() else None
        notes = get_notes_query(db, session["user_id"], search, sort, tag_id)
        result = [{
            "id": row["id"],
            "title": row["title"],
            "content": row["content"],
            "content_format": row["content_format"],
            "is_pinned": bool(row["is_pinned"]),
            "tags": get_note_tags(db, row["id"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"]
        } for row in notes]
    finally:
        db.close()
    return jsonify(result)


@app.route("/api/notes/trash", methods=["GET"])
@login_required
def get_trash():
    db = get_db()
    try:
        notes = db.execute(
            "SELECT * FROM notes WHERE user_id = ? AND is_deleted = 1 ORDER BY deleted_at DESC",
            (session["user_id"],)
        ).fetchall()
    finally:
        db.close()
    return jsonify([{
        "id": row["id"],
        "title": row["title"],
        "content": row["content"],
        "deleted_at": row["deleted_at"],
        "created_at": row["created_at"]
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
                "content_format": note["content_format"],
                "is_pinned": bool(note["is_pinned"]),
                "tags": get_note_tags(db, note["id"]),
                "created_at": note["created_at"],
                "updated_at": note["updated_at"]
            }
        })
    finally:
        db.close()


@app.route("/api/notes/<int:note_id>/pin", methods=["PUT"])
@login_required
def toggle_pin(note_id):
    db = get_db()
    try:
        note = db.execute("SELECT * FROM notes WHERE id = ? AND user_id = ?", (note_id, session["user_id"])).fetchone()
        if not note:
            return jsonify({"success": False, "message": "Note not found"}), 404

        new_val = 0 if note["is_pinned"] else 1
        db.execute("UPDATE notes SET is_pinned = ? WHERE id = ?", (new_val, note_id))
        db.commit()
        return jsonify({"success": True, "is_pinned": bool(new_val)})
    finally:
        db.close()


@app.route("/api/notes/<int:note_id>/trash", methods=["PUT"])
@login_required
def trash_note(note_id):
    db = get_db()
    try:
        note = db.execute("SELECT * FROM notes WHERE id = ? AND user_id = ?", (note_id, session["user_id"])).fetchone()
        if not note:
            return jsonify({"success": False, "message": "Note not found"}), 404

        db.execute("UPDATE notes SET is_deleted = 1, deleted_at = CURRENT_TIMESTAMP WHERE id = ?", (note_id,))
        db.commit()
        return jsonify({"success": True, "message": "Note moved to trash"})
    finally:
        db.close()


@app.route("/api/notes/<int:note_id>/restore", methods=["PUT"])
@login_required
def restore_note(note_id):
    db = get_db()
    try:
        note = db.execute("SELECT * FROM notes WHERE id = ? AND user_id = ?", (note_id, session["user_id"])).fetchone()
        if not note:
            return jsonify({"success": False, "message": "Note not found"}), 404

        db.execute("UPDATE notes SET is_deleted = 0, deleted_at = NULL WHERE id = ?", (note_id,))
        db.commit()
        return jsonify({"success": True, "message": "Note restored"})
    finally:
        db.close()


@app.route("/api/notes/<int:note_id>/permanent", methods=["DELETE"])
@login_required
def permanent_delete(note_id):
    db = get_db()
    try:
        note = db.execute("SELECT * FROM notes WHERE id = ? AND user_id = ?", (note_id, session["user_id"])).fetchone()
        if not note:
            return jsonify({"success": False, "message": "Note not found"}), 404

        db.execute("DELETE FROM note_tags WHERE note_id = ?", (note_id,))
        db.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        db.commit()
        return jsonify({"success": True, "message": "Note permanently deleted"})
    finally:
        db.close()


@app.route("/api/trash/empty", methods=["DELETE"])
@login_required
def empty_trash():
    db = get_db()
    try:
        note_ids = [r["id"] for r in db.execute("SELECT id FROM notes WHERE user_id = ? AND is_deleted = 1", (session["user_id"],)).fetchall()]
        if note_ids:
            placeholders = ",".join("?" * len(note_ids))
            db.execute(f"DELETE FROM note_tags WHERE note_id IN ({placeholders})", note_ids)
            db.execute(f"DELETE FROM notes WHERE id IN ({placeholders})", note_ids)
            db.commit()
        return jsonify({"success": True, "message": f"Trash emptied ({len(note_ids)} notes)"})
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
    content_format = data.get("content_format", "plain")
    tag_ids = data.get("tag_ids", [])

    if not title or not content:
        return jsonify({"success": False, "message": "Title and content are required"}), 400

    db = get_db()
    try:
        note_id = db.execute(
            "INSERT INTO notes (title, content, content_format, user_id) VALUES (?, ?, ?, ?)",
            (title, content, content_format, session["user_id"])
        ).lastrowid
        for tag_id in tag_ids:
            tag = db.execute("SELECT id FROM tags WHERE id = ? AND user_id = ?", (tag_id, session["user_id"])).fetchone()
            if tag:
                db.execute("INSERT OR IGNORE INTO note_tags (note_id, tag_id) VALUES (?, ?)", (note_id, tag_id))
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
            "content_format": note["content_format"],
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
    content_format = data.get("content_format", "plain")
    tag_ids = data.get("tag_ids", None)

    if not title or not content:
        return jsonify({"success": False, "message": "Title and content are required"}), 400

    db = get_db()
    try:
        existing = db.execute("SELECT * FROM notes WHERE id = ? AND user_id = ?", (note_id, session["user_id"])).fetchone()
        if not existing:
            return jsonify({"success": False, "message": "Note not found"}), 404

        db.execute(
            "UPDATE notes SET title = ?, content = ?, content_format = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ?",
            (title, content, content_format, note_id, session["user_id"])
        )
        if tag_ids is not None:
            db.execute("DELETE FROM note_tags WHERE note_id = ?", (note_id,))
            for tag_id in tag_ids:
                tag = db.execute("SELECT id FROM tags WHERE id = ? AND user_id = ?", (tag_id, session["user_id"])).fetchone()
                if tag:
                    db.execute("INSERT OR IGNORE INTO note_tags (note_id, tag_id) VALUES (?, ?)", (note_id, tag_id))
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
            "content_format": note["content_format"],
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

        db.execute("UPDATE notes SET is_deleted = 1, deleted_at = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ?", (note_id, session["user_id"]))
        db.commit()
    finally:
        db.close()

    return jsonify({"success": True, "message": "Note moved to trash"})


# ─── AI Routes ──────────────────────────────────────────────────

import ai


@app.route("/api/ai/config", methods=["GET"])
def ai_config():
    local = ai.local_available()
    return jsonify({
        "configured": ai.is_configured(),
        "model": ai.model(),
        "backend": ai.backend(),
        "local_available": local,
        "local_model": ai.local_model_name() if local else None,
        "actions": sorted(ai.ACTIONS),
        "daily_limit": ai.DAILY_LIMIT,
    })


@app.route("/api/ai/<action>", methods=["POST"])
@login_required
def ai_action(action):
    if action not in ai.ACTIONS:
        return jsonify({"success": False, "message": "Invalid action. Use: " + ", ".join(sorted(ai.ACTIONS))}), 400

    data = request.get_json(silent=True) or {}
    content = (data.get("content") or "").strip()
    provider = (data.get("provider") or "auto").lower()
    if not content:
        return jsonify({"success": False, "message": "No content to process"}), 400

    db = get_db()
    try:
        usage = get_ai_usage_today(db, session["user_id"])
        if usage >= ai.DAILY_LIMIT:
            return jsonify({"success": False, "message": "Daily AI limit reached (%d/day). Try again tomorrow." % ai.DAILY_LIMIT}), 429
    finally:
        db.close()

    try:
        use_local = provider == "local" or (
            provider == "auto" and not ai.is_configured() and ai.local_available()
        )
        if use_local:
            result_text, tokens = ai.run_local(action, content)
        else:
            result_text, tokens = ai.run(action, content, model_name=data.get("model"))
    except ai.AIError as exc:
        return jsonify({"success": False, "message": exc.message}), exc.status

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
        "backend": ai.backend(provider) if provider != "auto" else ai.backend(),
        "tokens_used": tokens,
        "remaining_today": max(0, ai.DAILY_LIMIT - (usage + 1))
    })


@app.route("/api/ai/usage", methods=["GET"])
@login_required
def ai_usage():
    db = get_db()
    try:
        usage = get_ai_usage_today(db, session["user_id"])
    finally:
        db.close()
    return jsonify({"used": usage, "limit": ai.DAILY_LIMIT, "remaining": max(0, ai.DAILY_LIMIT - usage)})


# ─── Tags Routes ───────────────────────────────────────────────

@app.route("/api/tags", methods=["GET"])
@login_required
def get_tags():
    db = get_db()
    try:
        tags = db.execute("SELECT * FROM tags WHERE user_id = ? ORDER BY name", (session["user_id"],)).fetchall()
    finally:
        db.close()
    return jsonify([{"id": t["id"], "name": t["name"], "color": t["color"]} for t in tags])


@app.route("/api/tags", methods=["POST"])
@login_required
def create_tag():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No data received"}), 400

    name = data.get("name", "").strip()
    color = data.get("color", "#7c5cff").strip()

    if not name:
        return jsonify({"success": False, "message": "Tag name is required"}), 400

    db = get_db()
    try:
        existing = db.execute("SELECT id FROM tags WHERE name = ? AND user_id = ?", (name, session["user_id"])).fetchone()
        if existing:
            return jsonify({"success": False, "message": "Tag already exists"}), 409

        tag_id = db.execute("INSERT INTO tags (name, color, user_id) VALUES (?, ?, ?)", (name, color, session["user_id"])).lastrowid
        db.commit()
    finally:
        db.close()

    return jsonify({"success": True, "tag": {"id": tag_id, "name": name, "color": color}}), 201


@app.route("/api/tags/<int:tag_id>", methods=["DELETE"])
@login_required
def delete_tag(tag_id):
    db = get_db()
    try:
        tag = db.execute("SELECT id FROM tags WHERE id = ? AND user_id = ?", (tag_id, session["user_id"])).fetchone()
        if not tag:
            return jsonify({"success": False, "message": "Tag not found"}), 404
        db.execute("DELETE FROM note_tags WHERE tag_id = ?", (tag_id,))
        db.execute("DELETE FROM tags WHERE id = ? AND user_id = ?", (tag_id, session["user_id"]))
        db.commit()
    finally:
        db.close()
    return jsonify({"success": True, "message": "Tag deleted"})


# ─── Export/Import Routes ──────────────────────────────────────

@app.route("/api/notes/export", methods=["GET"])
@login_required
def export_notes():
    db = get_db()
    try:
        notes = db.execute("SELECT * FROM notes WHERE user_id = ? ORDER BY created_at DESC", (session["user_id"],)).fetchall()
        export = []
        for note in notes:
            tags = get_note_tags(db, note["id"])
            export.append({
                "title": note["title"],
                "content": note["content"],
                "content_format": note["content_format"],
                "tags": [t["name"] for t in tags],
                "created_at": note["created_at"],
                "updated_at": note["updated_at"]
            })
    finally:
        db.close()

    return jsonify({
        "version": "1.0",
        "exported_at": __import__("datetime").datetime.utcnow().isoformat(),
        "notes_count": len(export),
        "notes": export
    })


@app.route("/api/notes/import", methods=["POST"])
@login_required
def import_notes():
    data = request.get_json()
    if not data or "notes" not in data:
        return jsonify({"success": False, "message": "Invalid import data"}), 400

    notes = data["notes"]
    if not isinstance(notes, list):
        return jsonify({"success": False, "message": "Notes must be a list"}), 400

    imported = 0
    db = get_db()
    try:
        for item in notes:
            title = item.get("title", "").strip()
            content = item.get("content", "").strip()
            content_format = item.get("content_format", "plain")
            tag_names = item.get("tags", [])

            if not title or not content:
                continue

            note_id = db.execute(
                "INSERT INTO notes (title, content, content_format, user_id) VALUES (?, ?, ?, ?)",
                (title, content, content_format, session["user_id"])
            ).lastrowid

            for tag_name in tag_names:
                tag_name = tag_name.strip()
                if not tag_name:
                    continue
                tag = db.execute("SELECT id FROM tags WHERE name = ? AND user_id = ?", (tag_name, session["user_id"])).fetchone()
                if not tag:
                    tag_id = db.execute("INSERT INTO tags (name, user_id) VALUES (?, ?)", (tag_name, session["user_id"])).lastrowid
                else:
                    tag_id = tag["id"]
                db.execute("INSERT OR IGNORE INTO note_tags (note_id, tag_id) VALUES (?, ?)", (note_id, tag_id))

            imported += 1
        db.commit()
    finally:
        db.close()

    return jsonify({"success": True, "message": f"Imported {imported} notes", "imported": imported})


# ─── User Settings Routes ──────────────────────────────────────

@app.route("/settings")
def settings_page():
    if "user_id" not in session:
        return redirect("/signin")
    return render_template("settings.html", username=session.get("username"))


@app.route("/api/settings/username", methods=["PUT"])
@login_required
def update_username():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No data received"}), 400

    new_username = data.get("username", "").strip()
    if not new_username or len(new_username) < 3:
        return jsonify({"success": False, "message": "Username must be at least 3 characters"}), 400

    db = get_db()
    try:
        existing = db.execute("SELECT id FROM users WHERE username = ? AND id != ?", (new_username, session["user_id"])).fetchone()
        if existing:
            return jsonify({"success": False, "message": "Username already taken"}), 409
        db.execute("UPDATE users SET username = ? WHERE id = ?", (new_username, session["user_id"]))
        db.commit()
        session["username"] = new_username
    finally:
        db.close()

    return jsonify({"success": True, "message": "Username updated"})


@app.route("/api/settings/password", methods=["PUT"])
@login_required
def update_password():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No data received"}), 400

    current = data.get("current_password", "").strip()
    new_password = data.get("new_password", "").strip()

    if not current or not new_password:
        return jsonify({"success": False, "message": "Both fields are required"}), 400

    if len(new_password) < 6:
        return jsonify({"success": False, "message": "New password must be at least 6 characters"}), 400

    db = get_db()
    try:
        user = db.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()
        if not user or not verify_password(current, user["password"]):
            return jsonify({"success": False, "message": "Current password is incorrect"}), 401
        db.execute("UPDATE users SET password = ? WHERE id = ?", (hash_password(new_password), session["user_id"]))
        db.commit()
    finally:
        db.close()

    return jsonify({"success": True, "message": "Password updated"})


@app.route("/api/settings/stats", methods=["GET"])
@login_required
def user_stats():
    db = get_db()
    try:
        notes_count = db.execute("SELECT COUNT(*) as c FROM notes WHERE user_id = ?", (session["user_id"],)).fetchone()["c"]
        tags_count = db.execute("SELECT COUNT(*) as c FROM tags WHERE user_id = ?", (session["user_id"],)).fetchone()["c"]
        ai_today = get_ai_usage_today(db, session["user_id"])
        ai_total = db.execute("SELECT COALESCE(SUM(tokens_used), 0) as t FROM ai_usage WHERE user_id = ?", (session["user_id"],)).fetchone()["t"]
    finally:
        db.close()

    return jsonify({
        "notes_count": notes_count,
        "tags_count": tags_count,
        "ai_today": ai_today,
        "ai_total_tokens": ai_total
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=os.environ.get("FLASK_DEBUG", "true").lower() == "true")
