from flask import Blueprint

auth_bp = Blueprint("auth", __name__, url_prefix="/api")

from auth.CREATE import create_username, create_password
from auth.GET import get_username, get_password
