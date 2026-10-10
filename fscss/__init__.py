import os

from flask import Blueprint, current_app, jsonify, render_template_string, request

from fscss.compiler import compile_fscss

fscss_bp = Blueprint("fscss", __name__)

_cache = {}

def _source_dir():
    configured = current_app.config.get("FSCSS_SOURCE_DIR")
    if configured:
        return configured
    return os.path.join(current_app.root_path, "static", "css")

def _resolve(name):
    name = os.path.basename(name)
    if not name.endswith(".fscss"):
        name += ".fscss"
    path = os.path.join(_source_dir(), name)
    if not os.path.isfile(path):
        return None
    return path

def _compile(name):
    cache_key = name
    path = _resolve(name)
    if not path:
        return None, None

    mtime = os.path.getmtime(path)
    entry = _cache.get(cache_key)
    if entry and entry[0] == mtime:
        return entry[1], path

    with open(path, "r", encoding="utf-8") as fh:
        source = fh.read()
    css = compile_fscss(source)
    _cache[cache_key] = (mtime, css)
    return css, path


@fscss_bp.route("/assets", methods=["GET"])
def fscss_index():
    source_dir = _source_dir()
    try:
        files = sorted(f for f in os.listdir(source_dir) if f.endswith(".fscss"))
    except FileNotFoundError:
        files = []
    css_urls = ["/assets/" + os.path.splitext(f)[0] + ".css" for f in files]
    page = "<h1>FSCSS assets</h1><ul>"
    for f, url in zip(files, css_urls):
        page += '<li><code>%s</code> &rarr; <a href="%s">%s</a></li>' % (f, url, url)
    page += "</ul>"
    return render_template_string(page)


@fscss_bp.route("/assets/<path:name>.css", methods=["GET"])
def fscss_serve(name):
    css, path = _compile(name)
    if css is None:
        return jsonify({"success": False, "message": "FSCSS source not found"}), 404

    headers = {
        "Content-Type": "text/css; charset=utf-8",
        "X-FSCSS-Source": os.path.basename(path),
        "Cache-Control": "no-cache",
    }
    if request.args.get("debug"):
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read(), 200, headers
    return css, 200, headers


@fscss_bp.route("/assets/compile", methods=["POST"])
def fscss_compile():
    data = request.get_json(force=True, silent=True) or {}
    source = data.get("fscss") or data.get("source")
    if not source:
        return jsonify({"success": False, "message": "fscss source required"}), 400
    try:
        css = compile_fscss(source)
    except Exception as exc:
        return jsonify({"success": False, "message": str(exc)}), 500
    return jsonify({"success": True, "css": css})


def clear_fscss_cache():
    _cache.clear()