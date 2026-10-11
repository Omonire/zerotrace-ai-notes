"""Runtime loading and prediction for the note classifier.

Loads ``ml/model.joblib`` lazily and caches it once. Exposes::

    ml_predict.is_available()          -> bool
    ml_predict.categories()            -> list[str]
    ml_predict.predict(text)           -> [{"category": str, "confidence": float}, ...]
"""

import math
import os

_MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.joblib")

_loaded = None
_load_error = None


def _load():
    global _loaded, _load_error
    if _loaded is not None or _load_error is not None:
        return _loaded
    try:
        import joblib
        with open(_MODEL_PATH, "rb") as fh:
            bundle = joblib.load(fh)
        _loaded = bundle
    except Exception as exc:  # noqa: BLE001 - surface any load problem to callers
        _load_error = "%s: %s" % (type(exc).__name__, exc)
        _loaded = None
    return _loaded


def is_available():
    return bool(_load())


def error():
    return _load_error


def categories():
    bundle = _load()
    if not bundle:
        return []
    return list(bundle["metadata"]["categories"])


def _softmax(values):
    shift = max(values)
    exp = [math.exp(v - shift) for v in values]
    total = sum(exp)
    return [e / total for e in exp]


def predict(text, top=3):
    """Return the top-n predicted categories with softmax confidence."""
    bundle = _load()
    if not bundle:
        return []
    text = (text or "").strip()
    if not text:
        return []

    pipeline = bundle["pipeline"]
    labels = bundle["metadata"]["categories"]
    scores = pipeline.decision_function([text])[0]
    confidences = _softmax(list(scores))

    ranked = sorted(
        ((labels[i], confidences[i], float(scores[i])) for i in range(len(labels))),
        key=lambda item: item[2],
        reverse=True,
    )
    return [{"category": c, "confidence": round(p, 4)} for c, p, _ in ranked[:top]]


def main():
    print("available:", is_available(), "| categories:", categories())
    for sample in [
        "Meeting with the client to review the Q3 roadmap and demo the new dashboard.",
        "Buy groceries and call mom for her birthday.",
        "Todo: deploy the patch, add error tracking, retry the build.",
    ]:
        print(sample[:40], "->", predict(sample))


if __name__ == "__main__":
    main()