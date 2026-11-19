from app.utils.time import utc_now
"""Explicit, repeatable development setup; never run seeds on application startup."""
from datetime import datetime, timedelta
import click
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash
from app import db
from app.models import AdminUser, ParkingSpot, ParkingZone, SpotHistory, SensorDevice


def register_commands(app):
    app.cli.add_command(seed_demo)
    app.cli.add_command(create_admin)
    app.cli.add_command(provision_device)


@click.command("create-admin")
@click.option("--email", prompt=True)
@click.option("--username", prompt=True)
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
@with_appcontext
def create_admin(email, username, password):
    """Create a super-admin without shipping any default credentials."""
    if len(password) < 8 or len(password) > 128 or not 3 <= len(username) <= 50 or "@" not in email:
        raise click.ClickException("Use a valid email, 3-50 character username and 8-128 character password.")
    if AdminUser.query.filter_by(email=email.strip().lower()).first():
        raise click.ClickException("That account already exists; no changes made.")
    db.session.add(AdminUser(email=email.strip().lower(), username=username,
        password_hash=generate_password_hash(password), role="super_admin", is_approved=True))
    db.session.commit()
    click.echo("Super-admin created.")


@click.command("seed-demo")
@with_appcontext
def seed_demo():
    """Populate an empty database with synthetic parking data; safe to rerun."""
    if ParkingSpot.query.first():
        click.echo("Parking data exists; nothing changed.")
        return
    zone = ParkingZone(name="Demo parking", city="Tunis")
    db.session.add(zone)
    db.session.flush()
    for side in "AB":
        for n in range(1, 13):
            status = "OUT_OF_SERVICE" if n == 12 else "OCCUPIED" if n % 3 == 0 else "FREE"
            spot = ParkingSpot(code=f"{side}{n}", zone_id=zone.id, status=status)
            db.session.add(spot)
            db.session.flush()
            for day in range(7):
                db.session.add(SpotHistory(spot_id=spot.id, old_status="FREE", new_status="OCCUPIED",
                    changed_at=utc_now() - timedelta(days=day, hours=n % 8),
                    source="SYSTEM", note="Synthetic demo event"))
    db.session.commit()
    click.echo("Created 24 synthetic parking spaces and seven days of example activity.")


@click.command("provision-device")
@click.option("--subject", required=True, type=click.UUID)
@click.option("--spot-code", required=True)
@with_appcontext
def provision_device(subject, spot_code):
    """Map one dedicated Supabase Auth user UUID to one parking spot."""
    spots = ParkingSpot.query.filter_by(code=spot_code).all()
    if len(spots) != 1:
        raise click.ClickException("Spot code must identify exactly one existing spot.")
    subject = str(subject)
    existing = SensorDevice.query.filter_by(subject=subject).first()
    if existing:
        if existing.spot_id != spots[0].id:
            raise click.ClickException("Device is already assigned elsewhere; no changes made.")
        click.echo("Device mapping already exists.")
        return
    if SensorDevice.query.filter_by(spot_id=spots[0].id).first():
        raise click.ClickException("Spot already has a device; no changes made.")
    db.session.add(SensorDevice(subject=subject, spot_id=spots[0].id))
    db.session.commit()
    click.echo("Device provisioned for the selected spot.")
