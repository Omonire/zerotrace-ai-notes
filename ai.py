"""Central AI integration for AI Notes.

Reads configuration from the environment and exposes a small, dependency-light
API used across the app:

    ai.is_configured()      -> bool
    ai.model()              -> str
    ai.run(action, content) -> (text, tokens)
    ai.complete(messages)   -> (text, tokens)

Three backends are supported:

    * ``puter``  - browser inference via Puter.js (handled in the frontend)
    * ``openai`` - server inference via the OpenAI Chat Completions API
    * ``local``  - the from-scratch transformer in ``ml/`` (needs PyTorch)

The server uses OpenAI when configured, otherwise the local model when a
checkpoint is available.
"""

import json
import os
import urllib.error
import urllib.request

DEFAULT_MODEL = "gpt-4o-mini"
DAILY_LIMIT = int(os.environ.get("AI_DAILY_LIMIT", "10"))
REQUEST_TIMEOUT = int(os.environ.get("OPENAI_TIMEOUT", "30"))
LOCAL_MODEL_PATH = os.environ.get("LOCAL_MODEL_PATH", "ml/runs/shakespeare-mini")

ACTIONS = {
    "summarize": "Summarize the following note concisely. Keep the key points and main ideas. Output only the summary, no preamble.",
    "expand": "Expand the following note with more detail, context, and depth. Keep the original meaning. Output only the expanded text.",
    "rewrite": "Rewrite the following note to be clearer and more polished. Keep the meaning but improve flow and readability. Output only the rewritten text.",
    "explain": "Explain the following note in simple, plain language for a beginner. Output only the explanation.",
    "title": "Generate a short, descriptive title (max 8 words) for the following note. Output only the title, no quotes.",
    "translate": "Translate the following note into English if it is not English, otherwise translate it into Spanish. Output only the translated text.",
    "todos": "Extract a concise bullet list of action items from the following note. Output only the list.",
}


class AIError(Exception):
    def __init__(self, message, status=502):
        super().__init__(message)
        self.message = message
        self.status = status


def api_key():
    return (os.environ.get("OPENAI_API_KEY") or "").strip()


def model():
    return (os.environ.get("OPENAI_MODEL") or "").strip() or DEFAULT_MODEL


def base_url():
    return (os.environ.get("OPENAI_BASE_URL") or "").strip() or None


def is_configured():
    return bool(api_key())


def local_available():
    """True when PyTorch is importable and a local checkpoint exists."""
    try:
        from ml import backend as local_backend
    except Exception:
        return False
    try:
        return local_backend.is_available(LOCAL_MODEL_PATH)
    except Exception:
        return False


def local_model_name():
    return os.path.basename(LOCAL_MODEL_PATH.rstrip("/\\")) or "local"


def backend(provider=None):
    """Resolve the server-side backend, honouring an explicit provider."""
    if provider == "local":
        return "local"
    if provider == "openai":
        return "openai"
    if provider == "puter":
        return "puter"
    if api_key():
        return "openai"
    if local_available():
        return "local"
    return "puter"


def _local_lm():
    try:
        from ml import backend as local_backend
    except Exception:
        raise AIError("Local model unavailable (PyTorch is not installed)", 503)
    try:
        return local_backend.get_local_model(LOCAL_MODEL_PATH)
    except Exception as exc:
        raise AIError("Local model unavailable: " + str(exc), 503)


def complete_local(messages, system=None, max_tokens=250):
    """Generate a chat reply with the local from-scratch model."""
    lm = _local_lm()
    reply = lm.chat(messages, notes_context=system or "", max_new_tokens=max_tokens)
    return reply, 0


def run_local(action, content, max_tokens=200):
    """Attempt a note action (summarize/expand/...) with the local model."""
    if action not in ACTIONS:
        raise AIError("Invalid action. Use: " + ", ".join(sorted(ACTIONS)), 400)
    content = (content or "").strip()
    if not content:
        raise AIError("No content to process", 400)
    lm = _local_lm()
    prompt = ACTIONS[action] + "\n\n" + content + "\n\nOutput:"
    text = lm.generate(prompt, max_new_tokens=max_tokens)
    return text.strip(), 0


def _client():
    try:
        from openai import OpenAI
    except ImportError:
        return None
    kwargs = {"api_key": api_key()}
    if base_url():
        kwargs["base_url"] = base_url()
    return OpenAI(**kwargs)


def _error_message(exc):
    for attr in ("message", "code"):
        value = getattr(exc, attr, None)
        if value:
            return str(value)
    response = getattr(exc, "response", None)
    if response is not None:
        try:
            body = response.json()
            message = body.get("error", {}).get("message")
            if message:
                return message
        except Exception:
            pass
    text = str(exc).strip()
    return text or "AI request failed"


def _http_chat(messages, model_name, max_tokens, temperature):
    payload = json.dumps({
        "model": model_name,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    })
    url = (base_url() or "https://api.openai.com/v1") + "/chat/completions"
    req = urllib.request.Request(
        url,
        data=payload.encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + api_key(),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        try:
            message = json.loads(body).get("error", {}).get("message")
        except Exception:
            message = None
        raise AIError(message or "AI request failed", 502)
    except urllib.error.URLError as exc:
        raise AIError("AI service unreachable: " + str(exc.reason), 502)

    text = result["choices"][0]["message"]["content"].strip()
    tokens = result.get("usage", {}).get("total_tokens", 0)
    return text, tokens


def complete(messages, model_name=None, max_tokens=2000, temperature=0.7, system=None):
    if not api_key():
        raise AIError("No AI backend is available", 503)

    model_name = (model_name or "").strip() or model()
    convo = []
    if system:
        convo.append({"role": "system", "content": system})
    convo.extend(messages)

    client = _client()
    if client is None:
        return _http_chat(convo, model_name, max_tokens, temperature)

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=convo,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    except Exception as exc:
        raise AIError(_error_message(exc), 502)

    text = (response.choices[0].message.content or "").strip()
    usage = getattr(response, "usage", None)
    tokens = getattr(usage, "total_tokens", 0) if usage else 0
    return text, tokens


def run(action, content, model_name=None, max_tokens=2000):
    if action not in ACTIONS:
        raise AIError("Invalid action. Use: " + ", ".join(sorted(ACTIONS)), 400)
    content = (content or "").strip()
    if not content:
        raise AIError("No content to process", 400)
    return complete(
        [{"role": "user", "content": content}],
        model_name=model_name,
        max_tokens=max_tokens,
        system=ACTIONS[action],
    )
