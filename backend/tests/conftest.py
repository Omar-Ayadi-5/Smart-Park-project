import os
import secrets
import pytest
from app import create_app, db
from app.models import AdminUser, ParkingZone, ParkingSpot
from werkzeug.security import generate_password_hash


@pytest.fixture
def app():
    application = create_app({"TESTING": True, "SECRET_KEY": secrets.token_hex(32),
        "SQLALCHEMY_DATABASE_URI": os.getenv("TEST_DATABASE_URL", "sqlite://"),
        "RATELIMIT_ENABLED": False,
        "CORS_ORIGINS": ["http://localhost:5173", "http://localhost:5174"]})
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def accounts(app):
    users = {}
    for role, approved, name in [("super_admin", True, "super"), ("admin", True, "admin"), ("admin", False, "pending")]:
        user = AdminUser(email=f"{name}@example.com", username=name, role=role,
            is_approved=approved, password_hash=generate_password_hash("Test-password-42!"))
        db.session.add(user)
        users[name] = user
    zone = ParkingZone(name="Test parking")
    db.session.add(zone)
    db.session.flush()
    for i, status in enumerate(["FREE", "OCCUPIED", "OUT_OF_SERVICE"], 1):
        db.session.add(ParkingSpot(code=f"A{i}", status=status, zone_id=zone.id))
    db.session.commit()
    return users


@pytest.fixture
def login(client, accounts):
    def authenticate(name="admin"):
        response = client.post("/api/admin/login", json={"email":f"{name}@example.com", "password":"Test-password-42!"})
        assert response.status_code == 200
        return {"Authorization": "Bearer " + response.json["token"]}
    return authenticate
