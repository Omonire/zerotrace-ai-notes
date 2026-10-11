import re

from flask import jsonify, request, session

from Bot import bot_bp
from database import get_db
import ai

SYSTEM_PROMPT = (
    "You are ZeroTrace AI, a concise, helpful assistant built into a note-taking app. "
    "You have access to the user's own notes, provided below as context. "
    "Answer using those notes whenever they are relevant, and cite the note title "
    "you are drawing from (e.g. 'from your note \"Trip to Porto\"'). "
    "If the notes do not contain the answer, say so and answer from general knowledge. "
    "Prefer short, practical answers and Markdown when formatting helps."
)

MAX_NOTES = 20
MAX_CHARS_PER_NOTE = 700
MAX_CONTEXT_CHARS = 8000
_WORD_RE = re.compile(r"[a-z0-9]+")


def _keyword_score(query, text):
    terms = set(_WORD_RE.findall(query.lower()))
    terms = {t for t in terms if len(t) > 2}
    if not terms:
        return 0
    words = set(_WORD_RE.findall(text.lower()))
    return len(terms & words)


def _load_notes(db, user_id, query):
    rows = db.execute(
        """
        SELECT n.id, n.title, n.content, n.is_pinned, n.updated_at,
               (SELECT GROUP_CONCAT(t.name, ', ')
                  FROM note_tags nt JOIN tags t ON t.id = nt.tag_id
                 WHERE nt.note_id = n.id) AS tags
          FROM notes n
         WHERE n.user_id = ? AND n.is_deleted = 0
         ORDER BY n.is_pinned DESC, n.updated_at DESC
        """,
        (user_id,),
    ).fetchall()

    scored = []
    for row in rows:
        text = "%s\n%s" % (row["title"] or "", row["content"] or "")
        score = _keyword_score(query, text)
        scored.append((score, row))

    if query.strip():
        scored.sort(key=lambda item: item[0], reverse=True)

    return [row for score, row in scored[:MAX_NOTES]]


def _build_context(notes):
    if not notes:
        return "The user has no notes yet."
    blocks = []
    used = 0
    for row in notes:
        content = (row["content"] or "").strip()
        if len(content) > MAX_CHARS_PER_NOTE:
            content = content[:MAX_CHARS_PER_NOTE].rstrip() + "..."
        tags = (" | tags: " + row["tags"]) if row["tags"] else ""
        block = 'Note #%s "%s"%s\n%s' % (row["id"], row["title"], tags, content)
        if used + len(block) > MAX_CONTEXT_CHARS:
            break
        blocks.append(block)
        used += len(block)
    return "\n\n---\n\n".join(blocks)


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

    query = clean[-1]["content"]
    notes = _load_notes(get_db(), session["user_id"], query)
    context = _build_context(notes)
    system = (
        SYSTEM_PROMPT
        + "\n\nThe user's notes (most relevant first):\n\n"
        + context
    )

    try:
        reply, tokens = ai.complete(clean[-20:], system=system, max_tokens=1500)
    except ai.AIError as exc:
        return jsonify({"success": False, "message": exc.message}), exc.status

    return jsonify({
        "success": True,
        "reply": reply,
        "tokens_used": tokens,
        "model": ai.model(),
        "sources": [{"id": row["id"], "title": row["title"]} for row in notes],
    })