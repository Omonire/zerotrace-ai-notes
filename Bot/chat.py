from flask import jsonify, request, session

from Bot import bot_bp
import ai

SYSTEM_PROMPT = (
    "You are ZeroTrace AI, a concise, helpful assistant built into a note-taking app. "
    "Help the user write, summarize, organize, and reason about their notes. "
    "Prefer short, practical answers and Markdown when formatting helps."
)


@bot_bp.route("/api/bot/chat", methods=["POST"])
def bot_chat():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Not signed in"}), 401

    data = request.get_json(silent=True) or {}
    messages = data.get("messages")

    if not isinstance(messages, list) or not messages:
        single = (data.get("message") or "").strip()
        if not single:
            return jsonify({"success": False, "message": "Provide 'message' or 'messages'"}), 400
        messages = [{"role": "user", "content": single}]

    clean = []
    for item in messages:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = (item.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            clean.append({"role": role, "content": content})

    if not clean:
        return jsonify({"success": False, "message": "No valid messages"}), 400

    if not ai.is_configured():
        return jsonify({"success": False, "message": "AI not configured. Set OPENAI_API_KEY in .env"}), 503

    try:
        reply, tokens = ai.complete(clean[-20:], system=SYSTEM_PROMPT, max_tokens=1500)
    except ai.AIError as exc:
        return jsonify({"success": False, "message": exc.message}), exc.status

    return jsonify({
        "success": True,
        "reply": reply,
        "tokens_used": tokens,
        "model": ai.model(),
    })
