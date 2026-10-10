from flask import jsonify, request
from auth import auth_bp
from database import get_db


@auth_bp.route("/create_username", methods=["POST"])
def create_username():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No data received"}), 400

    username = data.get("username", "").strip()
    if not username:
        return jsonify({"success": False, "message": "Username is required"}), 400

    db = get_db()
    try:
        existing = db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if existing:
            return jsonify({"success": False, "message": "Username already taken"}), 409

        db.execute(
            "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
            (username, username + "@legacy.local", "")
        )
        db.commit()
    finally:
        db.close()

    return jsonify({"success": True, "message": "Username created"}), 201
