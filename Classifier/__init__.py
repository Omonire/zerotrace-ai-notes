"""Classifier blueprint: local note classification (no external service)."""

from flask import Blueprint

classifier_bp = Blueprint("classifier", __name__)

from Classifier import routes  # noqa: E402,F401 — register routes