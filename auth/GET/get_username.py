from flask import jsonify, request
from auth import auth_bp
from database import get_db


@auth_bp.route("/get_username", methods=["GET"])
def get_username():
    username = request.args.get("username", "").strip()
    if not username:
        return jsonify({"success": False, "message": "Username parameter is required"}), 400

    db = get_db()
    try:
        user = db.execute(
            "SELECT id, username, created_at FROM users WHERE username = ?", (username,)
        ).fetchone()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404
        return jsonify({
            "success": True,
            "user": {
                "id": user["id"],
                "username": user["username"],
                "created_at": user["created_at"]
            }
        })
    finally:
        db.close()
