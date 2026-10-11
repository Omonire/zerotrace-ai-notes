from flask import jsonify, request, session

from Classifier import classifier_bp
from ml import predict


@classifier_bp.route("/api/ml/status", methods=["GET"])
def ml_status():
    return jsonify({
        "available": predict.is_available(),
        "categories": predict.categories(),
        "error": predict.error(),
    })


@classifier_bp.route("/api/ml/classify", methods=["POST"])
def ml_classify():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Not signed in"}), 401

    if not predict.is_available():
        return jsonify({
            "success": False,
            "message": "Model not available yet. Run: python -m ml.train",
        }), 503

    data = request.get_json(silent=True) or {}
    content = (data.get("content") or "").strip()
    if not content:
        return jsonify({"success": False, "message": "No content to classify"}), 400

    return jsonify({
        "success": True,
        "predictions": predict.predict(content),
        "categories": predict.categories(),
    })