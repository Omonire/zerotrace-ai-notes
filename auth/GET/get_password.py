from flask import jsonify, request
from auth import auth_bp
from database import get_db


@auth_bp.route("/get_password", methods=["GET"])
def get_password():
    username = request.args.get("username", "").strip()
    if not username:
        return jsonify({"success": False, "message": "Username parameter is required"}), 400

    db = get_db()
    try:
        user = db.execute("SELECT id, password FROM users WHERE username = ?", (username,)).fetchone()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404
        return jsonify({
            "success": True,
            "has_password": bool(user["password"])
        })
    finally:
        db.close()
