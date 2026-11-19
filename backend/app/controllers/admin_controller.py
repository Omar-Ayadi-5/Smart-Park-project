from app.utils.time import utc_now
import re
from collections import Counter
from datetime import datetime, timedelta, timezone

import jwt
from flask import current_app, g
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from app import db
from app.models import AdminUser, ParkingSpot, SpotHistory

# A dummy hash keeps unknown-user and wrong-password checks on the same code path.
_DUMMY_HASH = generate_password_hash("not-an-account-password")


def _internal_error():
    db.session.rollback()
    current_app.logger.exception("Database operation failed")
    return {"error": "An internal error occurred"}, 500


def register_admin(data):
    email, password, username = (data.get(k) for k in ("email", "password", "username"))
    if not all(isinstance(v, str) for v in (email, password, username)):
        return {"error": "Email, username, and password are required"}, 400
    email, username = email.strip().lower(), username.strip()
    if (len(email) > 100 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email)
            or not 3 <= len(username) <= 50 or not 8 <= len(password) <= 128):
        return {"error": "Use a valid email, a 3-50 character username, and an 8-128 character password"}, 400
    # Same response for existing and new accounts to avoid an email lookup endpoint.
    if AdminUser.query.filter_by(email=email).first():
        return {"success": True}, 201
    db.session.add(AdminUser(email=email, username=username,
                             password_hash=generate_password_hash(password)))
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
    return {"success": True}, 201


def login_admin(data):
    email, password = data.get("email"), data.get("password")
    if not isinstance(email, str) or not isinstance(password, str) or len(password) > 128:
        return {"error": "Invalid credentials"}, 401
    admin = AdminUser.query.filter_by(email=email.strip().lower()).first()
    correct = check_password_hash(admin.password_hash if admin else _DUMMY_HASH, password)
    if not admin or not correct:
        return {"error": "Invalid credentials"}, 401
    if not admin.is_approved:
        return {"error": "Account pending approval. Contact super admin."}, 403
    token = jwt.encode({"admin_id": admin.id,
                        "exp": datetime.now(timezone.utc) + timedelta(hours=24)},
                       current_app.config["SECRET_KEY"], algorithm="HS256")
    return {"token": token, "user": {"id": admin.id, "email": admin.email,
            "username": admin.username, "role": admin.role}}, 200


def get_dashboard_data():
    """Aggregate a seven-day window in UTC+1, identically on PostgreSQL and SQLite."""
    spots = ParkingSpot.query.all()
    counts = Counter(s.status for s in spots)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    local_now = now + timedelta(hours=1)
    week_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=local_now.weekday())
    events = SpotHistory.query.filter(SpotHistory.changed_at >= now - timedelta(days=7),
                                     SpotHistory.changed_at <= now,
                                     SpotHistory.new_status == "OCCUPIED").all()
    daily, weekly, heat = Counter(), Counter(), Counter()
    for event in events:
        local = event.changed_at + timedelta(hours=1)
        weekly[str(local.date())] += 1
        if event.changed_at >= now - timedelta(hours=24):
            daily[local.hour] += 1
        if local >= week_start:
            heat[(local.weekday(), local.hour)] += 1
    zones = sorted({s.zone_id for s in spots})
    return {
        "totalSpots": len(spots), "availableSpots": counts["FREE"],
        "occupiedSpots": counts["OCCUPIED"], "outOfServiceSpots": counts["OUT_OF_SERVICE"],
        "occupancyRate": round(counts["OCCUPIED"] / len(spots) * 100) if spots else 0,
        "zones": [{"name": f"Zone {z}", "occupied": round(
            sum(s.status == "OCCUPIED" for s in spots if s.zone_id == z) /
            sum(s.zone_id == z for s in spots) * 100)} for z in zones],
        "dailyTraffic": [{"hour": h, "count": daily[h]} for h in range(24)],
        "weeklyTrend": [{"day": str((local_now - timedelta(days=i)).date()),
                         "count": weekly[str((local_now - timedelta(days=i)).date())]} for i in range(6, -1, -1)],
        "heatmap": [{"day": d, "hour": h, "count": heat[(d, h)]}
                    for d in range(local_now.weekday() + 1) for h in range(24)]
    }

# UPDATE USERNAME
def update_username(admin_id, data):
    try:
        new_username = data.get("username")

        if not isinstance(new_username, str) or not 3 <= len(new_username.strip()) <= 50:
            return {"error": "Username is required"}, 400

        admin = db.session.get(AdminUser, admin_id)

        if not admin:
            return {"error": "Admin not found"}, 404

        admin.username = new_username.strip()
        db.session.commit()

        return {"success": True, "username": admin.username}, 200

    except Exception:
        return _internal_error()


# DELETE ACCOUNT
def delete_admin(admin_id):
    try:
        admin = db.session.get(AdminUser, admin_id)

        if not admin:
            return {"error": "Admin not found"}, 404

        # Suppression directe: si tu veux un “soft delete”, il faudra ajouter un flag en DB.
        db.session.delete(admin)
        db.session.commit()

        return {"success": True}, 200

    except Exception:
        return _internal_error()

def get_all_admins():
    admins = AdminUser.query.all()

    return [
        {
            "id": a.id,
            "email": a.email,
            "username": a.username,
            "role" : a.role,
            "is_approved": a.is_approved
        }
        for a in admins
    ]

def approve_admin(admin_id):
    admin = db.session.get(AdminUser, admin_id)

    if not admin:
        return {"error": "Not found"}, 404

    # L’approbation débloque le login (voir `login_admin`).
    admin.is_approved = True
    db.session.commit()

    return {"success": True}, 200

def toggle_spot_oos(spot_id):
    try:
        spot = db.session.get(ParkingSpot, spot_id)

        if not spot:
            return {"error": "Spot not found"}, 404

        old_status = spot.status

        # Règle métier: on ne permet pas de mettre une place OCCUPIED en “hors service”
        # pour éviter des incohérences (voiture présente mais place désactivée).
        if old_status == "OCCUPIED":
            return {"error": "Cannot modify occupied spot"}, 400

        # Bascule: OUT_OF_SERVICE ↔ FREE uniquement.
        if old_status == "OUT_OF_SERVICE":
            new_status = "FREE"
            note = "Restored to service by admin"
        else:
            new_status = "OUT_OF_SERVICE"
            note = "Marked out of service by admin"

        # =============================
        # INSERT HISTORY (LIKE YOUR SQL)
        # =============================
        history = SpotHistory(
            changed_at=utc_now(),
            old_status=old_status,
            new_status=new_status,
            source="ADMIN",
            note=note,
            spot_id=spot.id,
            # `g.admin_id` vient du JWT (middleware `token_required`).
            changed_by_admin_id=g.admin_id
        )

        db.session.add(history)

        # =============================
        # UPDATE SPOT
        # =============================
        spot.status = new_status
        spot.last_updated = utc_now()

        db.session.commit()

        return {
            "success": True,
            "status": new_status
        }, 200

    except Exception:
        db.session.rollback()
        return _internal_error()
