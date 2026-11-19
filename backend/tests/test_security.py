from datetime import datetime, timedelta, timezone
import jwt
import pytest
from sqlalchemy.exc import SQLAlchemyError
from app import db, create_app
from app.models import AdminUser


def test_registration_is_pending_and_password_is_hashed(client):
    payload = {"email":"new@example.com", "username":"newuser", "password":"Test-password-42!"}
    assert client.post("/api/admin/register", json=payload).status_code == 201
    user = AdminUser.query.one()
    assert not user.is_approved and user.role == "admin"
    assert user.password_hash != payload["password"]
    assert client.post("/api/admin/login", json=payload).status_code == 403
    assert client.post("/api/admin/register", json=payload).json == {"success":True}
    assert AdminUser.query.count() == 1


@pytest.mark.parametrize("payload", [[], None, {"email":"bad", "username":"ok", "password":"short"},
    {"email":42, "username":"user", "password":"long-enough"}])
def test_bad_registration_is_rejected(client, payload):
    response = client.post("/api/admin/register", json=payload)
    assert response.status_code in (400, 415)
    assert AdminUser.query.count() == 0


def test_login_does_not_expose_account_existence(client, accounts):
    bodies = [client.post("/api/admin/login", json={"email":email,"password":"wrong"})
              for email in ["missing@example.com", "admin@example.com"]]
    assert [r.status_code for r in bodies] == [401, 401]
    assert bodies[0].json == bodies[1].json


def test_deleted_account_token_is_rejected(client, login):
    headers = login()
    assert client.delete("/api/admin/delete-account", headers=headers).status_code == 200
    assert client.get("/api/admin/dashboard", headers=headers).status_code == 401


def test_unapproved_account_token_is_rejected(client, login, accounts):
    headers = login()
    accounts["admin"].is_approved = False
    db.session.commit()
    assert client.get("/api/admin/dashboard", headers=headers).status_code == 401


def test_current_database_role_overrides_old_claims(client, app, accounts):
    forged_stale_role = jwt.encode({"admin_id":accounts["admin"].id,"role":"super_admin",
        "exp":datetime.now(timezone.utc)+timedelta(minutes=5)},app.config["SECRET_KEY"],algorithm="HS256")
    response=client.put(f'/api/admin/approve-admin/{accounts["pending"].id}',headers={"Authorization":"Bearer "+forged_stale_role})
    assert response.status_code == 403
    assert not accounts["pending"].is_approved


def test_super_admin_approves_then_user_can_login(client, login, accounts):
    response=client.put(f'/api/admin/approve-admin/{accounts["pending"].id}',headers=login("super"))
    assert response.status_code == 200
    assert login("pending")


@pytest.mark.parametrize("kind", ["expired", "wrong_signature", "missing_exp", "invalid_id"])
def test_invalid_tokens(client, app, accounts, kind):
    payload={"admin_id":accounts["admin"].id,"exp":datetime.now(timezone.utc)+timedelta(minutes=5)}
    key=app.config["SECRET_KEY"]
    if kind=="expired":payload["exp"]=datetime.now(timezone.utc)-timedelta(seconds=1)
    if kind=="wrong_signature":key="another-key-that-is-at-least-32-characters"
    if kind=="missing_exp":payload.pop("exp")
    if kind=="invalid_id":payload["admin_id"]="1"
    token=jwt.encode(payload,key,algorithm="HS256")
    assert client.get("/api/admin/dashboard",headers={"Authorization":"Bearer "+token}).status_code==401


def test_login_rate_limit():
    import secrets
    application=create_app({"TESTING":True,"SECRET_KEY":secrets.token_hex(32),
        "SQLALCHEMY_DATABASE_URI":"sqlite://", "RATELIMIT_ENABLED":True})
    with application.app_context():
        db.create_all()
        client=application.test_client()
        responses=[client.post('/api/admin/login',json={"email":"missing@example.com","password":"wrong"}) for _ in range(11)]
        assert responses[-1].status_code == 429
        db.drop_all()


def test_internal_error_is_redacted(client, login, monkeypatch):
    headers=login()
    def broken(*args,**kwargs):
        raise SQLAlchemyError("private-database-password")
    monkeypatch.setattr(db.session,"commit",broken)
    response=client.put('/api/admin/update-username',json={"username":"changed"},headers=headers)
    assert response.status_code == 500
    assert 'private-database-password' not in response.get_data(as_text=True)


def test_cors_allows_only_configured_origins(client):
    headers={"Origin":"http://localhost:5173","Access-Control-Request-Method":"POST"}
    assert client.options('/api/admin/login',headers=headers).headers['Access-Control-Allow-Origin']==headers['Origin']
    headers['Origin']='https://untrusted.example'
    assert 'Access-Control-Allow-Origin' not in client.options('/api/admin/login',headers=headers).headers


@pytest.mark.parametrize("scheme", ["postgres", "postgresql", "postgresql+psycopg2"])
def test_host_postgres_urls_use_installed_driver(scheme):
    import secrets
    application=create_app({"TESTING": True, "SECRET_KEY": secrets.token_hex(32),
        "SQLALCHEMY_DATABASE_URI": scheme+"://user:placeholder@localhost/unused",
        "RATELIMIT_ENABLED": False})
    with application.app_context():
        assert db.engine.dialect.driver == "psycopg2"
        db.engine.dispose()
