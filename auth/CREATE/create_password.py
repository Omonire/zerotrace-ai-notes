import hashlib
from flask import jsonify, request
from auth import auth_bp
from database import get_db


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


@auth_bp.route("/create_password", methods=["POST"])
def create_password():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No data received"}), 400

    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    if not username or not password:
        return jsonify({"success": False, "message": "Username and password are required"}), 400

    db = get_db()
    try:
        user = db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        db.execute("UPDATE users SET password = ? WHERE username = ?", (hash_password(password), username))
        db.commit()
    finally:
        db.close()

    return jsonify({"success": True, "message": "Password set successfully"})
