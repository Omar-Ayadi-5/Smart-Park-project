from functools import wraps

import jwt
from flask import current_app, g, jsonify, request
from jwt.exceptions import InvalidTokenError

from app import db
from app.models import AdminUser


def token_required(view):
    """Verify the signature and expiry, then authorize against current account state."""
    @wraps(view)
    def decorated(*args, **kwargs):
        parts = request.headers.get("Authorization", "").split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return jsonify(error="A Bearer token is required"), 401
        try:
            payload = jwt.decode(parts[1], current_app.config["SECRET_KEY"],
                                 algorithms=["HS256"], options={"require": ["exp", "admin_id"]})
            admin_id = payload["admin_id"]
            if type(admin_id) is not int:
                raise InvalidTokenError("Invalid account ID")
        except InvalidTokenError:
            return jsonify(error="Invalid or expired token"), 401
        admin = db.session.get(AdminUser, admin_id)
        if not admin or not admin.is_approved or admin.role not in {"admin", "super_admin"}:
            return jsonify(error="Account is no longer authorized"), 401
        # Never trust a stale role embedded in an already issued JWT.
        g.admin_id, g.admin_email, g.role = admin.id, admin.email, admin.role
        return view(*args, **kwargs)
    return decorated
